@echo off
REM Runs the Midterm's garak latent-injection probes against the layered configuration of the running rag_server.py (port 8095).
REM Start the server first:  python rag_server.py
set PY=D:\Work\garak-env\Scripts\python.exe
cd /d "%~dp0.."
set PROBES=probes.latentinjection.LatentInjectionFactSnippetEiffel,probes.latentinjection.LatentInjectionFactSnippetLegal,probes.latentinjection.LatentInjectionReport
"%PY%" -m garak --target_type rest -G configs\rest_layered.json --config configs\run_layered.yaml --spec %PROBES% --report_prefix latentinjection > logs\garak_layered\garak_console.log 2>&1
