import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import uuid

from jarvisx.database.session import get_db
from jarvisx.database.models import Team, TeamMember, TeamWorkspace, User, Organization, Workspace
from services.api.admin.src.models.teams import (
    TeamCreate, TeamUpdate, TeamResponse, TeamDetailResponse,
    TeamMemberCreate, TeamMemberUpdate, TeamMemberResponse,
    TeamWorkspaceResponse,
    UserInvite, UserResponse,
    ResendOTPRequest, VerificationResponse, SetPasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)
from jarvisx.services.email import EmailService
from services.api.admin.src.dependencies import get_current_user, CurrentUser
from services.api.admin.src.auth import hash_password
from services.api.admin.src.permissions import Resource, Action
from services.api.admin.src.decorators import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teams", tags=["teams"])


def get_team_response(team: Team, db: Session) -> TeamResponse:
    member_count = db.query(func.count(TeamMember.id)).filter(
        TeamMember.team_id == team.id,
        TeamMember.is_active == True
    ).scalar()
    
    org = db.query(Organization).filter(Organization.id == team.organization_id).first()
    
    scoped_workspace_count = 0
    if not team.scope_all_workspaces:
        scoped_workspace_count = db.query(func.count(TeamWorkspace.id)).filter(
            TeamWorkspace.team_id == team.id
        ).scalar()
    
    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        role=team.role,
        is_default=team.is_default,
        is_active=team.is_active,
        scope_all_workspaces=team.scope_all_workspaces,
        created_at=team.created_at,
        updated_at=team.updated_at,
        member_count=member_count,
        organization_name=org.name if org else None,
        scoped_workspace_count=scoped_workspace_count
    )


@router.get("", response_model=List[TeamResponse])
def get_teams(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    query = db.query(Team)
    
    if not current_user.is_platform_admin:
        query = query.filter(Team.organization_id == current_user.organization_id)
    
    teams = query.order_by(Team.name).all()
    return [get_team_response(team, db) for team in teams]


@router.get("/verify-email", response_model=VerificationResponse)
def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    email_service = EmailService(db)
    success, message, user = email_service.verify_email_token(token, mark_used=False)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return VerificationResponse(
        success=True,
        message="Please set your password to activate your account.",
        user_id=user.id if user else None,
        email=user.email if user else None,
        first_name=user.first_name if user else None
    )


@router.post("/set-password", response_model=VerificationResponse)
def set_password(
    data: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    email_service = EmailService(db)
    success, message, user = email_service.activate_user_with_password(
        data.token,
        hash_password(data.password)
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return VerificationResponse(success=True, message="Account activated successfully. You can now sign in.")


@router.post("/resend-verification", response_model=VerificationResponse)
def resend_verification(
    resend_request: ResendOTPRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    base_url = request.headers.get("origin") or request.headers.get("referer", "").rstrip("/") or "http://localhost:5003"
    base_url = base_url.rstrip("/")
    
    email_service = EmailService(db)
    success, message = email_service.resend_verification_email(resend_request.user_id, base_url)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return VerificationResponse(success=True, message=message)


@router.post("/forgot-password", response_model=VerificationResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    base_url = request.headers.get("origin") or request.headers.get("referer", "").rstrip("/") or "http://localhost:5003"
    base_url = base_url.rstrip("/")
    
    email_service = EmailService(db)
    success, message = email_service.create_password_reset_token(data.email, base_url)
    
    return VerificationResponse(success=True, message=message)


@router.get("/reset-password/verify", response_model=VerificationResponse)
def verify_reset_token(
    token: str,
    db: Session = Depends(get_db)
):
    email_service = EmailService(db)
    success, message, user = email_service.verify_email_token(token, mark_used=False)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return VerificationResponse(
        success=True,
        message="Token is valid.",
        user_id=user.id if user else None,
        email=user.email if user else None,
        first_name=user.first_name if user else None
    )


@router.post("/reset-password", response_model=VerificationResponse)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    email_service = EmailService(db)
    success, message, user = email_service.reset_password(
        data.token,
        hash_password(data.password)
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return VerificationResponse(success=True, message="Password reset successfully. You can now sign in.")


@router.get("/{team_id}", response_model=TeamDetailResponse)
def get_team(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if not current_user.is_platform_admin and team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    member_responses = []
    
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        member_responses.append(TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            is_active=member.is_active,
            created_at=member.created_at,
            user_email=user.email if user else None,
            user_first_name=user.first_name if user else None,
            user_last_name=user.last_name if user else None
        ))
    
    scoped_workspaces = []
    if not team.scope_all_workspaces:
        team_workspaces = db.query(TeamWorkspace).filter(TeamWorkspace.team_id == team_id).all()
        for tw in team_workspaces:
            workspace = db.query(Workspace).filter(Workspace.id == tw.workspace_id).first()
            if workspace:
                scoped_workspaces.append(TeamWorkspaceResponse(
                    id=tw.id,
                    team_id=tw.team_id,
                    workspace_id=tw.workspace_id,
                    workspace_name=workspace.name,
                    created_at=tw.created_at
                ))
    
    org = db.query(Organization).filter(Organization.id == team.organization_id).first()
    member_count = len([m for m in members if m.is_active])
    
    return TeamDetailResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        role=team.role,
        is_default=team.is_default,
        is_active=team.is_active,
        scope_all_workspaces=team.scope_all_workspaces,
        created_at=team.created_at,
        updated_at=team.updated_at,
        member_count=member_count,
        organization_name=org.name if org else None,
        scoped_workspace_count=len(scoped_workspaces),
        members=member_responses,
        scoped_workspaces=scoped_workspaces
    )


@router.post("", response_model=TeamResponse)
@require_permission(Resource.TEAMS, Action.CREATE)
def create_team(
    team_data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    org_id = team_data.organization_id or current_user.organization_id
    
    if not current_user.is_platform_admin and org_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Cannot create team for another organization")
    
    existing = db.query(Team).filter(
        Team.organization_id == org_id,
        Team.name == team_data.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Team with this name already exists in the organization")
    
    team = Team(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        name=team_data.name,
        description=team_data.description,
        role=team_data.role,
        is_default=False,
        is_active=True,
        scope_all_workspaces=team_data.scope_all_workspaces
    )
    
    db.add(team)
    db.flush()
    
    if not team_data.scope_all_workspaces and team_data.workspace_ids:
        for workspace_id in team_data.workspace_ids:
            workspace = db.query(Workspace).filter(
                Workspace.id == workspace_id,
                Workspace.organization_id == org_id
            ).first()
            if workspace:
                team_workspace = TeamWorkspace(
                    id=str(uuid.uuid4()),
                    team_id=team.id,
                    workspace_id=workspace_id
                )
                db.add(team_workspace)
    
    db.commit()
    db.refresh(team)
    
    return get_team_response(team, db)


@router.put("/{team_id}", response_model=TeamResponse)
@require_permission(Resource.TEAMS, Action.EDIT)
def update_team(
    team_id: str,
    team_data: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if not current_user.is_platform_admin and team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if team_data.name is not None:
        existing = db.query(Team).filter(
            Team.organization_id == team.organization_id,
            Team.name == team_data.name,
            Team.id != team_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Team with this name already exists")
        team.name = team_data.name
    
    if team_data.description is not None:
        team.description = team_data.description
    
    if team_data.role is not None:
        team.role = team_data.role
    
    if team_data.is_active is not None:
        if team.is_default and not team_data.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate default team")
        team.is_active = team_data.is_active
    
    if team_data.scope_all_workspaces is not None:
        team.scope_all_workspaces = team_data.scope_all_workspaces
        
        if team_data.scope_all_workspaces:
            db.query(TeamWorkspace).filter(TeamWorkspace.team_id == team_id).delete()
    
    if team_data.workspace_ids is not None and not team.scope_all_workspaces:
        db.query(TeamWorkspace).filter(TeamWorkspace.team_id == team_id).delete()
        
        for workspace_id in team_data.workspace_ids:
            workspace = db.query(Workspace).filter(
                Workspace.id == workspace_id,
                Workspace.organization_id == team.organization_id
            ).first()
            if workspace:
                team_workspace = TeamWorkspace(
                    id=str(uuid.uuid4()),
                    team_id=team.id,
                    workspace_id=workspace_id
                )
                db.add(team_workspace)
    
    db.commit()
    db.refresh(team)
    
    return get_team_response(team, db)


@router.delete("/{team_id}")
@require_permission(Resource.TEAMS, Action.DELETE)
def delete_team(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if not current_user.is_platform_admin and team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if team.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default team")
    
    db.delete(team)
    db.commit()
    
    return {"message": "Team deleted successfully"}


@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
def get_team_members(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if not current_user.is_platform_admin and team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    result = []
    
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        result.append(TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            is_active=member.is_active,
            created_at=member.created_at,
            user_email=user.email if user else None,
            user_first_name=user.first_name if user else None,
            user_last_name=user.last_name if user else None
        ))
    
    return result


@router.post("/{team_id}/members", response_model=TeamMemberResponse)
@require_permission(Resource.TEAMS, Action.MANAGE)
def add_team_member(
    team_id: str,
    member_data: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if not current_user.is_platform_admin and team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = db.query(User).filter(User.id == member_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.organization_id != team.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to the same organization")
    
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == member_data.user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member of this team")
    
    member = TeamMember(
        id=str(uuid.uuid4()),
        team_id=team_id,
        user_id=member_data.user_id,
        is_active=True
    )
    
    db.add(member)
    db.commit()
    db.refresh(member)
    
    return TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        user_id=member.user_id,
        is_active=member.is_active,
        created_at=member.created_at,
        user_email=user.email,
        user_first_name=user.first_name,
        user_last_name=user.last_name
    )


@router.put("/{team_id}/members/{member_id}", response_model=TeamMemberResponse)
@require_permission(Resource.TEAMS, Action.MANAGE)
def update_team_member(
    team_id: str,
    member_id: str,
    member_data: TeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if not current_user.is_platform_admin and team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    if member_data.is_active is not None:
        member.is_active = member_data.is_active
    
    db.commit()
    db.refresh(member)
    
    user = db.query(User).filter(User.id == member.user_id).first()
    
    return TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        user_id=member.user_id,
        is_active=member.is_active,
        created_at=member.created_at,
        user_email=user.email if user else None,
        user_first_name=user.first_name if user else None,
        user_last_name=user.last_name if user else None
    )


@router.delete("/{team_id}/members/{member_id}")
@require_permission(Resource.TEAMS, Action.MANAGE)
def remove_team_member(
    team_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if not current_user.is_platform_admin and team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    db.delete(member)
    db.commit()
    
    return {"message": "Team member removed successfully"}


@router.get("/organization/{org_id}/users", response_model=List[UserResponse])
def get_organization_users(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not current_user.is_platform_admin and org_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    users = db.query(User).filter(User.organization_id == org_id).order_by(User.email).all()
    
    return [UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        effective_role=user.effective_role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at
    ) for user in users]


@router.get("/organization/{org_id}/workspaces")
def get_organization_workspaces(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not current_user.is_platform_admin and org_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    workspaces = db.query(Workspace).filter(
        Workspace.organization_id == org_id,
        Workspace.is_active == True
    ).order_by(Workspace.name).all()
    
    return [{"id": w.id, "name": w.name} for w in workspaces]


@router.post("/organization/{org_id}/users", response_model=UserResponse)
@require_permission(Resource.USERS, Action.CREATE)
def invite_user(
    org_id: str,
    invite_data: UserInvite,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not current_user.is_platform_admin and org_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = db.query(User).filter(User.email == invite_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    temp_password = f"temp_{uuid.uuid4().hex[:8]}"
    
    user = User(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        email=invite_data.email,
        password_hash=hash_password(temp_password),
        first_name=invite_data.first_name,
        last_name=invite_data.last_name,
        is_active=False,
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    base_url = request.headers.get("origin") or request.headers.get("referer", "").rstrip("/") or "http://localhost:5003"
    base_url = base_url.rstrip("/")
    
    try:
        email_service = EmailService(db)
        token, _ = email_service.create_verification_token(user.id, org_id)
        email_service.send_verification_email(user, token, base_url)
    except Exception as e:
        logger.error("[invite_user] Failed to send verification email: %s", e)
    
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        effective_role=user.effective_role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at
    )
