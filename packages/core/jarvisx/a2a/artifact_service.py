import logging
import pickle
from typing import Optional, Any
from sqlalchemy import String, LargeBinary, Integer, DateTime, Float, Text, func
from sqlalchemy.orm import Mapped, mapped_column, Session as DBSession
from sqlalchemy.dialects.postgresql import JSONB
from typing_extensions import override

from google.genai import types
from google.adk.artifacts.base_artifact_service import BaseArtifactService, ArtifactVersion
from jarvisx.a2a.base_storage import Base, BaseDatabaseStorageService

logger = logging.getLogger(__name__)

DEFAULT_MAX_KEY_LENGTH = 128


class StorageArtifact(Base):
    
    __tablename__ = "artifacts"
    
    app_name: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True, default="default")
    workspace_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True, default="default")
    filename: Mapped[str] = mapped_column(String(512), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    artifact_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50))
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    custom_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    create_time: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())


class DatabaseArtifactService(BaseDatabaseStorageService, BaseArtifactService):
    
    def __init__(self, db_url: str, schema: str = "jarvisx", workspace_id: str = "default", tenant_id: str = "default"):
        BaseDatabaseStorageService.__init__(self, db_url, schema, workspace_id, tenant_id)
        Base.metadata.schema = schema
        Base.metadata.create_all(self.engine)
    
    @override
    async def save_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        artifact: types.Part,
        session_id: Optional[str] = None,
        custom_metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        import time
        db: DBSession = self.SessionLocal()
        try:
            effective_session_id = session_id or "user"
            
            max_version = db.query(func.max(StorageArtifact.version)).filter_by(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
                filename=filename
            ).scalar()
            
            version = (max_version + 1) if max_version is not None else 0
            
            artifact_data = pickle.dumps(artifact)
            artifact_type = "text" if hasattr(artifact, 'text') and artifact.text else "inline_data"
            mime_type = None
            if hasattr(artifact, 'inline_data') and artifact.inline_data:
                mime_type = getattr(artifact.inline_data, 'mime_type', None)
            
            storage_artifact = StorageArtifact(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
                filename=filename,
                version=version,
                artifact_data=artifact_data,
                artifact_type=artifact_type,
                mime_type=mime_type,
                custom_metadata=custom_metadata or {},
                create_time=time.time()
            )
            
            db.add(storage_artifact)
            db.commit()
            
            logger.debug(f"Saved artifact {filename} version {version} for {app_name}/{user_id}/{session_id}, tenant {self.tenant_id}, workspace {self.workspace_id}")
            return version
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving artifact: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    @override
    async def load_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        db: DBSession = self.SessionLocal()
        try:
            effective_session_id = session_id or "user"
            
            query = db.query(StorageArtifact).filter_by(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
                filename=filename
            )
            
            if version is not None:
                query = query.filter_by(version=version)
            else:
                query = query.order_by(StorageArtifact.version.desc()).limit(1)
            
            storage_artifact = query.first()
            
            if not storage_artifact:
                return None
            
            artifact = pickle.loads(storage_artifact.artifact_data)
            logger.debug(f"Loaded artifact {filename} version {storage_artifact.version}, tenant {self.tenant_id}, workspace {self.workspace_id}")
            return artifact
        except Exception as e:
            logger.error(f"Error loading artifact: {e}", exc_info=True)
            return None
        finally:
            db.close()
    
    @override
    async def list_artifact_keys(
        self, *, app_name: str, user_id: str, session_id: Optional[str] = None
    ) -> list[str]:
        db: DBSession = self.SessionLocal()
        try:
            user_artifacts = db.query(StorageArtifact.filename).filter_by(
                app_name=app_name,
                user_id=user_id,
                session_id="user",
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id
            ).distinct().all()
            
            filenames = [f[0] for f in user_artifacts]
            
            if session_id:
                session_artifacts = db.query(StorageArtifact.filename).filter_by(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id,
                    tenant_id=self.tenant_id,
                    workspace_id=self.workspace_id
                ).distinct().all()
                filenames.extend([f[0] for f in session_artifacts])
            
            return sorted(set(filenames))
        except Exception as e:
            logger.error(f"Error listing artifacts: {e}", exc_info=True)
            return []
        finally:
            db.close()
    
    @override
    async def delete_artifact(
        self, *, app_name: str, user_id: str, filename: str, session_id: Optional[str] = None
    ) -> None:
        db: DBSession = self.SessionLocal()
        try:
            effective_session_id = session_id or "user"
            
            db.query(StorageArtifact).filter_by(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
                filename=filename
            ).delete()
            
            db.commit()
            logger.debug(f"Deleted artifact {filename} for {app_name}/{user_id}/{session_id}, tenant {self.tenant_id}, workspace {self.workspace_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting artifact: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    @override
    async def list_versions(
        self, *, app_name: str, user_id: str, filename: str, session_id: Optional[str] = None
    ) -> list[int]:
        db: DBSession = self.SessionLocal()
        try:
            effective_session_id = session_id or "user"
            
            versions = db.query(StorageArtifact.version).filter_by(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
                filename=filename
            ).order_by(StorageArtifact.version).all()
            
            return [v[0] for v in versions]
        except Exception as e:
            logger.error(f"Error listing artifact versions: {e}", exc_info=True)
            return []
        finally:
            db.close()
    
    @override
    async def list_artifact_versions(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> list[ArtifactVersion]:
        db: DBSession = self.SessionLocal()
        try:
            effective_session_id = session_id or "user"
            
            artifacts = db.query(StorageArtifact).filter_by(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
                filename=filename
            ).order_by(StorageArtifact.version).all()
            
            result = []
            for artifact in artifacts:
                canonical_uri = f"db://{self.tenant_id}/{self.workspace_id}/{app_name}/{user_id}/{effective_session_id}/{filename}@{artifact.version}"
                result.append(ArtifactVersion(
                    version=artifact.version,
                    canonical_uri=canonical_uri,
                    custom_metadata=artifact.custom_metadata or {},
                    create_time=artifact.create_time or artifact.created_at.timestamp() if artifact.created_at else 0.0,
                    mime_type=artifact.mime_type
                ))
            
            return result
        except Exception as e:
            logger.error(f"Error listing artifact versions: {e}", exc_info=True)
            return []
        finally:
            db.close()
    
    @override
    async def get_artifact_version(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[ArtifactVersion]:
        db: DBSession = self.SessionLocal()
        try:
            effective_session_id = session_id or "user"
            
            query = db.query(StorageArtifact).filter_by(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
                filename=filename
            )
            
            if version is not None:
                query = query.filter_by(version=version)
            else:
                query = query.order_by(StorageArtifact.version.desc()).limit(1)
            
            artifact = query.first()
            
            if not artifact:
                return None
            
            canonical_uri = f"db://{self.tenant_id}/{self.workspace_id}/{app_name}/{user_id}/{effective_session_id}/{filename}@{artifact.version}"
            return ArtifactVersion(
                version=artifact.version,
                canonical_uri=canonical_uri,
                custom_metadata=artifact.custom_metadata or {},
                create_time=artifact.create_time or artifact.created_at.timestamp() if artifact.created_at else 0.0,
                mime_type=artifact.mime_type
            )
        except Exception as e:
            logger.error(f"Error getting artifact version: {e}", exc_info=True)
            return None
        finally:
            db.close()
