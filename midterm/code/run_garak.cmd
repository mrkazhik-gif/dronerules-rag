@echo off
REM Runs the same garak latent-injection probes against both configurations of the running rag_server.py (port 8095).
REM Start the server first:  python rag_server.py
set PY=D:\Work\garak-env\Scripts\python.exe
cd /d "%~dp0.."
set PROBES=probes.latentinjection.LatentInjectionFactSnippetEiffel,probes.latentinjection.LatentInjectionFactSnippetLegal,probes.latentinjection.LatentInjectionReport
for %%C in (baseline source_aware) do (
  echo ##### RUN %%C %DATE% %TIME%
  "%PY%" -m garak --target_type rest -G configs\rest_%%C.json --config configs\run_%%C.yaml --spec %PROBES% --report_prefix latentinjection > "logs\garak_%%C\garak_console.log" 2>&1
)
echo ##### ALL DONE %DATE% %TIME%
