@echo off
echo.
echo ============================
echo ENVIANDO ATUALIZAÇÕES PARA O GITHUB
echo ============================

REM Define a mensagem de commit automaticamente com data e hora
set MSG=Atualização - %DATE% %TIME%

git add .
git commit -m "%MSG%"
git push origin main

echo.
echo ============================
echo DEPLOY ENVIADO COM SUCESSO!
echo ============================
pause
