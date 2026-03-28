#!/usr/bin/env python3
import subprocess
import time
import sys
import signal
import os
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "packages" / "core"))

from jarvisx.config.configs import (
    UI_REACT_VOICE_CHAT_PORT,
    ADMIN_API_PORT,
    ADMIN_UI_PORT,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_DB,
    POSTGRES_SCHEMA,
    LANGFUSE_ENABLED,
)
from jarvisx.config import VOICE_GATEWAY_PORT

LANGFUSE_PORT = int(os.environ.get("LANGFUSE_PORT", "3100"))


def _extract_port_from_url(url: str | None, default_port: int) -> int:
    if not url:
        return default_port
    try:
        parsed = urlparse(url)
        if parsed.port:
            return parsed.port
        return default_port
    except Exception:
        return default_port

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

processes = []

def print_status(message, color=BLUE):
    print(f"{color}[*] {message}{RESET}")

def print_success(message):
    print(f"{GREEN}[✓] {message}{RESET}")

def print_error(message):
    print(f"{RED}[✗] {message}{RESET}")

def print_warning(message):
    print(f"{YELLOW}[!] {message}{RESET}")

def check_port(host: str, port: int, timeout: int = 30) -> bool:
    import socket
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def wait_for_service(name: str, host: str, port: int, timeout: int = 30):
    print_status(f"Waiting for {name} to start on {host}:{port}...")
    if check_port(host, port, timeout):
        print_success(f"{name} is ready!")
        return True
    else:
        print_error(f"{name} failed to start within {timeout} seconds")
        return False

def start_langfuse():
    """Start LangFuse services using Docker Compose."""
    if not LANGFUSE_ENABLED:
        print_warning("LangFuse is disabled (LANGFUSE_ENABLED=false). Skipping...")
        return True
    
    print_status("Starting LangFuse observability services...")
    
    docker_compose_cmd = None
    for cmd in ["docker compose", "docker-compose"]:
        try:
            result = subprocess.run(
                cmd.split() + ["--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                docker_compose_cmd = cmd.split()
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not docker_compose_cmd:
        print_warning("Docker Compose not found. Skipping LangFuse services.")
        return True
    
    try:
        docker_compose_file = PROJECT_ROOT / "infra" / "docker" / "docker-compose.yml"
        if not docker_compose_file.exists():
            print_warning("docker-compose.yml not found. Skipping LangFuse services.")
            return True
        
        langfuse_already_running = check_port("localhost", LANGFUSE_PORT, timeout=2)
        
        if langfuse_already_running:
            print_success(f"LangFuse is already running on localhost:{LANGFUSE_PORT}")
            return True
        
        print_status("Starting LangFuse infrastructure (postgres, clickhouse, redis, minio, server)...")
        result = subprocess.run(
            docker_compose_cmd + ["up", "-d", "langfuse-postgres", "langfuse-clickhouse", "langfuse-redis", "langfuse-minio", "langfuse"],
            cwd=PROJECT_ROOT / "infra" / "docker",
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            print_warning(f"Failed to start LangFuse services: {result.stderr}")
            print_warning("Continuing without LangFuse observability...")
            return True
        
        print_status("Waiting for LangFuse to be ready (this may take a minute)...")
        if wait_for_service("LangFuse", "localhost", LANGFUSE_PORT, timeout=90):
            print_success(f"LangFuse is ready at http://localhost:{LANGFUSE_PORT}")
            print_status("Note: Create API keys in LangFuse UI and add to .env file")
        else:
            print_warning("LangFuse did not start in time. Continuing without it...")
            print_warning("You can check logs with: docker compose logs langfuse")
        
        return True
        
    except subprocess.TimeoutExpired:
        print_warning("Timeout while starting LangFuse. Continuing without it...")
        return True
    except Exception as e:
        print_warning(f"Failed to start LangFuse: {e}. Continuing without it...")
        return True


def start_postgresql_and_redis():
    """Start PostgreSQL and Redis using Docker Compose."""
    print_status("Starting infrastructure services (PostgreSQL, Redis)...")

    docker_compose_cmd = None
    for cmd in ["docker compose", "docker-compose"]:
        try:
            result = subprocess.run(
                cmd.split() + ["--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                docker_compose_cmd = cmd.split()
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    if not docker_compose_cmd:
        print_error("Docker Compose not found. Please install Docker and Docker Compose.")
        print_warning("You can start services manually with: docker compose up -d")
        return False

    try:
        docker_compose_file = PROJECT_ROOT / "infra" / "docker" / "docker-compose.yml"
        if not docker_compose_file.exists():
            print_error(f"docker-compose.yml not found at {docker_compose_file}")
            print_warning("Please ensure docker-compose.yml exists in the infra/docker/ folder.")
            return False

        postgres_port_int = int(POSTGRES_PORT)
        postgres_already_running = check_port(POSTGRES_HOST, postgres_port_int, timeout=2)

        # Check Redis
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_already_running = check_port(redis_host, redis_port, timeout=2)

        if postgres_already_running and redis_already_running:
            print_success(f"PostgreSQL is already running on {POSTGRES_HOST}:{postgres_port_int}")
            print_success(f"Redis is already running on {redis_host}:{redis_port}")
        else:
            services_to_start = []
            if not postgres_already_running:
                services_to_start.append("postgres")
            if not redis_already_running:
                services_to_start.append("redis")

            if services_to_start:
                print_status(f"Starting services: {', '.join(services_to_start)}")
                print_status(f"Running: {' '.join(docker_compose_cmd)} up -d {' '.join(services_to_start)}")
                result = subprocess.run(
                    docker_compose_cmd + ["up", "-d"] + services_to_start,
                    cwd=PROJECT_ROOT / "infra" / "docker",
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    print_error(f"Failed to start services: {result.stderr}")
                    return False

                print_success("Docker services started")

            # Wait for PostgreSQL
            if not postgres_already_running:
                print_status("Waiting for PostgreSQL to be ready...")
                if not wait_for_service("PostgreSQL", POSTGRES_HOST, postgres_port_int, timeout=30):
                    print_error("PostgreSQL failed to become ready")
                    print_warning("You can check logs with: docker compose logs postgres")
                    return False

            # Wait for Redis
            if not redis_already_running:
                print_status("Waiting for Redis to be ready...")
                if not wait_for_service("Redis", redis_host, redis_port, timeout=30):
                    print_warning("Redis failed to become ready")
                    print_warning("SSO state storage will fall back to in-memory mode")
                    # Don't fail - Redis is optional, will fallback to in-memory


        print_status(f"Ensuring database '{POSTGRES_DB}' and schema '{POSTGRES_SCHEMA}' exist...")
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=postgres_port_int,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (POSTGRES_DB,)
            )
            db_exists = cursor.fetchone()

            if not db_exists:
                print_status(f"Creating database '{POSTGRES_DB}'...")
                cursor.execute(f'CREATE DATABASE "{POSTGRES_DB}"')
                print_success(f"Database '{POSTGRES_DB}' created!")
            else:
                print_success(f"Database '{POSTGRES_DB}' already exists")

            cursor.close()
            conn.close()

            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=postgres_port_int,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB
            )
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {POSTGRES_SCHEMA}")
            cursor.close()
            conn.close()
            print_success(f"Schema '{POSTGRES_SCHEMA}' is ready!")
        except Exception as e:
            print_warning(f"Could not create database/schema automatically: {e}")
            print_warning("Database and schema will be created automatically when services initialize")

        return True
            
    except subprocess.TimeoutExpired:
        print_error("Timeout while starting PostgreSQL")
        return False
    except FileNotFoundError:
        print_error("Docker not found. Please install Docker.")
        return False
    except Exception as e:
        print_error(f"Failed to start PostgreSQL: {e}")
        return False

GATEWAY_CONFIGS = [
    ("voice", "Voice Gateway", VOICE_GATEWAY_PORT, "services.gateways.voice.src"),
]


def start_gateway(gateway_code: str, name: str, port: int, module: str) -> bool:
    print_status(f"Starting {name} (port {port})...")
    try:
        print_status(f"Running: uv run python3 -m {module}")
        env = {**os.environ}
        env["PYTHONPATH"] = f"{PROJECT_ROOT / 'packages' / 'core'}:{PROJECT_ROOT}"
        process = subprocess.Popen(
            ["uv", "run", "python3", "-m", module],
            stdout=None,
            stderr=None,
            cwd=PROJECT_ROOT,
            env=env
        )
        processes.append((name, process))
        
        time.sleep(2)
        if process.poll() is not None:
            exit_code = process.returncode
            print_error(f"{name} process exited immediately with code {exit_code}")
            return False
        
        if wait_for_service(name, "localhost", port):
            return True
        
        if process.poll() is not None:
            exit_code = process.returncode
            print_error(f"{name} process crashed with exit code {exit_code}")
        return False
    except Exception as e:
        print_error(f"Failed to start {name}: {e}")
        return False


def start_all_gateways() -> bool:
    for gateway_code, name, port, module in GATEWAY_CONFIGS:
        if not start_gateway(gateway_code, name, port, module):
            return False
        time.sleep(2)
    return True

def signal_handler(sig, frame):
    print_status("\nShutting down all services...")
    cleanup()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    kill_processes_on_ports()

    print_status("=" * 60)
    print_status("STARTING ALL JARVISX SERVICES")
    print_status("=" * 60)

    # Step 1: Start infrastructure (PostgreSQL, Redis)
    print_status("\n[1/5] Starting infrastructure services...")
    if not start_postgresql_and_redis():
        print_error("Failed to start infrastructure services.")
        print_warning("You can start services manually with: docker compose up -d")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print_status("Exiting...")
            sys.exit(1)
        print_warning("Continuing without infrastructure - services may fail if they need database/Redis connection.")
    
    time.sleep(2)

    # Step 2: Start Langfuse (optional observability)
    print_status("\n[2/5] Starting LangFuse observability (optional)...")
    start_langfuse()

    time.sleep(2)

    # Step 3: Run database migrations
    print_status("\n[3/5] Running database migrations...")
    print_status("=" * 60)
    try:
        print_status("Running: uv run alembic -c migrations/alembic.ini upgrade head")
        result = subprocess.run(
            ["uv", "run", "alembic", "-c", "migrations/alembic.ini", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print_success("✓ Database migrations completed successfully!")
            if result.stdout:
                print_status("\nMigration details:")
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        if "Running upgrade" in line or "INFO" in line:
                            print_status(f"  {line}")
            print_success("\nDatabase schema is up to date:")
            print_success("  • Organizations, users, teams")
            print_success("  • SSO configurations (OAuth2/OIDC, SAML)")
            print_success("  • Encryption keys with versioning")
            print_success("  • Workspaces, agents, workflows")
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print_error(f"Database migration failed: {error_msg}")
            raise Exception(error_msg)
    except FileNotFoundError:
        print_warning("'uv' command not found. Trying 'alembic' directly...")
        try:
            result = subprocess.run(
                ["alembic", "-c", "migrations/alembic.ini", "upgrade", "head"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print_success("✓ Database migrations completed")
            else:
                raise Exception(result.stderr or result.stdout)
        except FileNotFoundError:
            print_error("Neither 'uv' nor 'alembic' command found.")
            print_warning("Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
            print_warning("Or ensure alembic is in PATH")
            print_error("\nManual migration command:")
            print_error("  uv run alembic -c migrations/alembic.ini upgrade head")
            cleanup()
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print_error("Migration timed out after 120 seconds")
        print_error("This may indicate database connection issues")
        cleanup()
        sys.exit(1)
    except Exception as e:
        print_error(f"Could not run database migrations: {e}")
        print_error("\nMigration failed. Please check:")
        print_error("  1. PostgreSQL is running: docker compose ps")
        print_error("  2. Database credentials in .env file")
        print_error("  3. Network connectivity to database")
        print_error("\nManual migration command:")
        print_error("  uv run alembic -c migrations/alembic.ini upgrade head")
        cleanup()
        sys.exit(1)
    print_status("=" * 60)
    
    time.sleep(2)

    # Step 4: Start backend services (Gateways + Admin API)
    print_status("\n[4/5] Starting backend services...")
    print_status("=" * 60)

    if not start_all_gateways():
        print_error("Failed to start one or more gateways. Exiting...")
        cleanup()
        sys.exit(1)

    print_status(f"\nStarting Admin API (port {ADMIN_API_PORT})...")
    try:
        print_status("Running: uv run python3 -m services.api.admin.src")
        env = {**os.environ}
        env["PYTHONPATH"] = f"{PROJECT_ROOT / 'packages' / 'core'}:{PROJECT_ROOT}"
        process = subprocess.Popen(
            ["uv", "run", "python3", "-m", "services.api.admin.src"],
            stdout=None,
            stderr=None,
            cwd=PROJECT_ROOT,
            env=env
        )
        processes.append(("Admin API", process))
        time.sleep(2)
        if process.poll() is not None:
            exit_code = process.returncode
            print_error(f"Admin API process exited immediately with code {exit_code}")
            cleanup()
            sys.exit(1)
        elif wait_for_service("Admin API", "localhost", ADMIN_API_PORT, timeout=30):
            print_success("Admin API started")
        else:
            print_error("Admin API failed to start. Exiting...")
            cleanup()
            sys.exit(1)
    except Exception as e:
        print_error(f"Failed to start Admin API: {e}")
        cleanup()
        sys.exit(1)
    
    time.sleep(2)

    # Step 5: Start frontend services (Admin UI + Voice Chat UI)
    print_status("\n[5/5] Starting frontend services...")
    print_status("=" * 60)

    print_status(f"\nStarting Admin UI (port {ADMIN_UI_PORT})...")
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        admin_ui_dir = PROJECT_ROOT / "apps" / "admin"
        if not admin_ui_dir.exists():
            print_warning("Admin UI directory not found. Skipping Admin UI.")
        elif not (admin_ui_dir / "package.json").exists():
            print_warning("Admin UI package.json not found. Skipping Admin UI.")
        else:
            try:
                subprocess.run(["npm", "--version"], capture_output=True, timeout=5, check=True)
            except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
                print_warning("npm not found. Please install Node.js and npm. Skipping Admin UI.")
            else:
                if not (admin_ui_dir / "node_modules").exists():
                    print_warning("Admin UI node_modules not found.")
                    print_status("Run 'npm install' in apps/admin to install dependencies.")
                    print_warning("Skipping Admin UI for now.")
                else:
                    env = {**os.environ, "PORT": str(ADMIN_UI_PORT)}
                    process = subprocess.Popen(
                        ["npm", "run", "start"],
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        cwd=admin_ui_dir,
                        env=env
                    )
                    processes.append(("Admin UI", process))
                    time.sleep(3)
                    if wait_for_service("Admin UI", "localhost", ADMIN_UI_PORT, timeout=60):
                        print_success("Admin UI started")
                    else:
                        if process.poll() is not None:
                            exit_code = process.returncode
                            print_warning(f"Admin UI process exited with code {exit_code}")
                            if exit_code == 127:
                                print_warning("Exit code 127 usually means 'command not found'. Check npm/node installation.")
                            print_warning("Continuing without Admin UI...")
                        else:
                            print_warning("Admin UI failed to start. Continuing without it...")
    except Exception as e:
        print_error(f"Failed to start Admin UI: {e}")
        cleanup()
        sys.exit(1)
    
    time.sleep(2)

    print_status(f"\nStarting React Voice Chat App (port {UI_REACT_VOICE_CHAT_PORT})...")
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        voice_chat_dir = PROJECT_ROOT / "apps" / "chat"
        if not voice_chat_dir.exists():
            print_warning("Voice chat directory not found. Skipping React app.")
        elif not (voice_chat_dir / "package.json").exists():
            print_warning("Voice chat package.json not found. Skipping React app.")
        else:
            try:
                subprocess.run(["npm", "--version"], capture_output=True, timeout=5, check=True)
            except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
                print_warning("npm not found. Please install Node.js and npm. Skipping Voice Chat UI.")
            else:
                if not (voice_chat_dir / "node_modules").exists():
                    print_warning("Voice Chat UI node_modules not found.")
                    print_status("Run 'npm install' in apps/chat to install dependencies.")
                    print_warning("Skipping Voice Chat UI for now.")
                else:
                    env = {**os.environ, "PORT": str(UI_REACT_VOICE_CHAT_PORT)}
                    process = subprocess.Popen(
                        ["npm", "run", "start"],
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        cwd=voice_chat_dir,
                        env=env
                    )
                    processes.append(("React Voice Chat", process))
                    time.sleep(3)
                    if wait_for_service("React Voice Chat", "localhost", UI_REACT_VOICE_CHAT_PORT, timeout=60):
                        print_success("React Voice Chat started")
                    else:
                        if process.poll() is not None:
                            exit_code = process.returncode
                            print_warning(f"React Voice Chat process exited with code {exit_code}")
                            if exit_code == 127:
                                print_warning("Exit code 127 usually means 'command not found'. Check npm/node installation.")
                            print_warning("Continuing without React Voice Chat...")
                        else:
                            print_warning("React Voice Chat failed to start. Continuing without it...")
    except Exception as e:
        print_error(f"Failed to start React Voice Chat: {e}")
        cleanup()
        sys.exit(1)
    
    print_success("\n" + "="*60)
    print_success("🎉 ALL SERVICES STARTED SUCCESSFULLY!")
    print_success("="*60)

    print_status("\n📋 Infrastructure Status:")
    postgres_status = "✓ Running" if check_port(POSTGRES_HOST, int(POSTGRES_PORT), timeout=1) else "✗ Not responding"
    redis_status = "✓ Running" if check_port("localhost", int(os.environ.get("REDIS_PORT", "6379")), timeout=1) else "✗ Not responding"
    print_status(f"  • PostgreSQL:     {postgres_status}")
    print_status(f"  • Redis:          {redis_status}")
    print_status(f"  • Migrations:     ✓ Up to date")
    if LANGFUSE_ENABLED:
        langfuse_status = "✓ Running" if check_port("localhost", LANGFUSE_PORT, timeout=1) else "✗ Not responding"
        print_status(f"  • LangFuse:       {langfuse_status}")

    print_status("\n🚀 Application Services:")
    for name, process in processes:
        if process.poll() is None:
            print_success(f"  ✓ {name}")
        else:
            print_error(f"  ✗ {name} (exited)")

    print_status("\n" + "="*60)
    print_status("🌐 Access Points:")
    print_status(f"  • Admin UI:        http://localhost:{ADMIN_UI_PORT}")
    print_status(f"  • Admin API:       http://localhost:{ADMIN_API_PORT}")
    print_status(f"  • Voice Chat UI:   http://localhost:{UI_REACT_VOICE_CHAT_PORT}")
    print_status(f"  • Voice Gateway:   http://localhost:{VOICE_GATEWAY_PORT}")
    if LANGFUSE_ENABLED:
        print_status(f"  • LangFuse UI:     http://localhost:{LANGFUSE_PORT}")
    print_status("="*60)

    print_status("\n💡 Quick Tips:")
    print_status("  • Check logs: docker compose logs -f [postgres|redis]")
    print_status("  • Run migrations manually: uv run alembic upgrade head")
    print_status("  • Stop services: Press Ctrl+C")
    print_status("\n" + "="*60)
    print_status("📡 Monitoring services...")
    print_status("="*60 + "\n")
    
    try:
        while True:
            time.sleep(1)
            for name, process in list(processes):
                if process.poll() is not None:
                    print_error(f"{name} has stopped unexpectedly (exit code: {process.returncode})")
                    processes.remove((name, process))
    except KeyboardInterrupt:
        print_status("\nShutting down all services...")
        cleanup()
        sys.exit(0)

def kill_processes_on_ports():
    killed_any = False
    ports = [
        9003,  # VOICE_GATEWAY default
        UI_REACT_VOICE_CHAT_PORT,
        ADMIN_API_PORT,
        ADMIN_UI_PORT,
    ]
    try:
        import psutil
        for port in ports:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        connections = proc.net_connections()
                        for conn in connections:
                            if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                                print_warning(f"Found process {proc.info['name']} (PID {proc.info['pid']}) using port {port}, terminating...")
                                proc.terminate()
                                try:
                                    proc.wait(timeout=3)
                                except psutil.TimeoutExpired:
                                    proc.kill()
                                print_success(f"Terminated process on port {port}")
                                killed_any = True
                                time.sleep(1)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.Error):
                        pass
            except Exception:
                try:
                    result = subprocess.run(
                        ["lsof", "-ti", f":{port}"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            try:
                                pid_int = int(pid.strip())
                                os.kill(pid_int, signal.SIGTERM)
                                print_warning(f"Terminated process {pid_int} on port {port}")
                                killed_any = True
                                time.sleep(1)
                                try:
                                    os.kill(pid_int, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            except (ValueError, ProcessLookupError, PermissionError):
                                pass
                except Exception:
                    pass
    except ImportError:
        for port in ports:
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            pid_int = int(pid.strip())
                            os.kill(pid_int, signal.SIGTERM)
                            print_warning(f"Terminated process {pid_int} on port {port}")
                            killed_any = True
                            time.sleep(1)
                            try:
                                os.kill(pid_int, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        except (ValueError, ProcessLookupError, PermissionError):
                            pass
            except Exception:
                pass
    
    if killed_any:
        time.sleep(2)

def cleanup():
    for name, process in processes:
        try:
            print_status(f"Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print_success(f"{name} stopped")
        except Exception as e:
            print_error(f"Error stopping {name}: {e}")
    
    print_success("All services stopped")

if __name__ == "__main__":
    main()
