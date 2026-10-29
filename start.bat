@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === HR Screener: запуск ===

if not exist .env copy .env.example .env >nul

docker info >nul 2>&1
if %errorlevel%==0 goto docker
echo Docker не запущен или не установлен - запускаю без Docker (SQLite, Python, Node).
goto local

:docker
echo [Docker] Собираю и поднимаю контейнеры, первый раз это 3-5 минут...
docker compose up --build -d
if errorlevel 1 (
  echo Docker compose завершился с ошибкой, пробую запуск без Docker.
  goto local
)
call :wait_api
python scripts\seed.py || py scripts\seed.py
start "" http://localhost:3000
echo Готово: UI http://localhost:3000 , API http://localhost:8000/docs
goto end

:local
where python >nul 2>&1 && (set PY=python) || (set PY=py)
%PY% --version || (echo Нужен Python 3.11+: https://www.python.org/downloads/ & goto end)
where npm >nul 2>&1 || (echo Нужен Node.js 20+: https://nodejs.org/ & goto end)

cd backend
if not exist .venv (
  echo [Python] Создаю виртуальное окружение...
  %PY% -m venv .venv
)
echo [Python] Ставлю зависимости...
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\python -m pip install -q -r requirements.txt || .venv\Scripts\python -m pip install -q fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" pgvector pydantic pydantic-settings python-multipart pypdf python-docx anthropic openai httpx celery redis mcp PyJWT
set DATABASE_URL=sqlite:///./app.db
set CELERY_EAGER=true
set REDIS_URL=redis://localhost:6379/0
start "HR Screener API" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --port 8000"
cd ..\frontend
echo [Node] Ставлю зависимости фронтенда...
call npm install --no-audit --no-fund
start "HR Screener UI" cmd /k "npm run dev"
cd ..
call :wait_api
backend\.venv\Scripts\python scripts\seed.py
timeout /t 3 >nul
start "" http://localhost:5173
echo Демо-вход: HR hr@koz.demo / koz-demo-2026, кандидат candidate@koz.demo / koz-demo-2026
echo Готово: UI http://localhost:5173 , API http://localhost:8000/docs
goto end

:wait_api
echo Жду, пока поднимется API...
for /l %%i in (1,1,60) do (
  powershell -NoProfile -Command "try{(Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/health).StatusCode}catch{exit 1}" >nul 2>&1 && exit /b 0
  timeout /t 2 >nul
)
echo API не ответил за 2 минуты - посмотрите окно "HR Screener API".
exit /b 0

:end
echo.
pause
