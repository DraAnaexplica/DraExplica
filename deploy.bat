@echo off
echo.
echo ============================
echo INICIANDO DEPLOY AUTOMÁTICO
echo ============================
git add .
git commit -m "Atualização automática"
git push origin master
echo.
echo ============================
echo DEPLOY ENVIADO COM SUCESSO!
echo ============================
pause
