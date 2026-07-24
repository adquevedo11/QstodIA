@echo off
set KEY=C:\Users\AndresFelipeQuevedoV\.ssh\devops.pem
set SERVER=azureuser@172.208.11.6
set REMOTE=~/defectdojo-sqa

echo Subiendo cambios de hoy...

scp -i %KEY% dojo/static/dojo/css/sqa-theme.css %SERVER%:%REMOTE%/dojo/static/dojo/css/sqa-theme.css
scp -i %KEY% dojo/templates/base.html %SERVER%:%REMOTE%/dojo/templates/base.html
scp -i %KEY% dojo/templates/dojo/login.html %SERVER%:%REMOTE%/dojo/templates/dojo/login.html
scp -i %KEY% dojo/templates/400.html %SERVER%:%REMOTE%/dojo/templates/400.html
scp -i %KEY% dojo/templates/403.html %SERVER%:%REMOTE%/dojo/templates/403.html
scp -i %KEY% dojo/templates/404.html %SERVER%:%REMOTE%/dojo/templates/404.html
scp -i %KEY% dojo/templates/500.html %SERVER%:%REMOTE%/dojo/templates/500.html
scp -i %KEY% dojo/templates/dojo/finding_pdf_report.html %SERVER%:%REMOTE%/dojo/templates/dojo/finding_pdf_report.html
scp -i %KEY% dojo/templates/dojo/go_live_readiness.html %SERVER%:%REMOTE%/dojo/templates/dojo/go_live_readiness.html
scp -i %KEY% dojo/templates/dojo/go_live_readiness_card.html %SERVER%:%REMOTE%/dojo/templates/dojo/go_live_readiness_card.html
scp -i %KEY% dojo/templates/dojo/go_live_readiness_content.html %SERVER%:%REMOTE%/dojo/templates/dojo/go_live_readiness_content.html
scp -i %KEY% dojo/static/dojo/img/qustodIA_logo3.png %SERVER%:%REMOTE%/dojo/static/dojo/img/qustodIA_logo3.png
scp -i %KEY% dojo/static/dojo/img/qustodIA_logo_2.png %SERVER%:%REMOTE%/dojo/static/dojo/img/qustodIA_logo_2.png
scp -i %KEY% dojo/executive_report/__init__.py %SERVER%:%REMOTE%/dojo/executive_report/__init__.py
scp -i %KEY% dojo/executive_report/urls.py %SERVER%:%REMOTE%/dojo/executive_report/urls.py
scp -i %KEY% dojo/executive_report/views.py %SERVER%:%REMOTE%/dojo/executive_report/views.py
scp -i %KEY% dojo/go_live_readiness/__init__.py %SERVER%:%REMOTE%/dojo/go_live_readiness/__init__.py
scp -i %KEY% dojo/go_live_readiness/urls.py %SERVER%:%REMOTE%/dojo/go_live_readiness/urls.py
scp -i %KEY% dojo/go_live_readiness/views.py %SERVER%:%REMOTE%/dojo/go_live_readiness/views.py
scp -i %KEY% dojo/security_concept/__init__.py %SERVER%:%REMOTE%/dojo/security_concept/__init__.py
scp -i %KEY% dojo/security_concept/urls.py %SERVER%:%REMOTE%/dojo/security_concept/urls.py
scp -i %KEY% dojo/security_concept/views.py %SERVER%:%REMOTE%/dojo/security_concept/views.py
scp -i %KEY% dojo/sqa_metrics/__init__.py %SERVER%:%REMOTE%/dojo/sqa_metrics/__init__.py
scp -i %KEY% dojo/sqa_metrics/urls.py %SERVER%:%REMOTE%/dojo/sqa_metrics/urls.py
scp -i %KEY% dojo/sqa_metrics/views.py %SERVER%:%REMOTE%/dojo/sqa_metrics/views.py
scp -i %KEY% dojo/db_migrations/0249_securityconcept.py %SERVER%:%REMOTE%/dojo/db_migrations/0249_securityconcept.py
scp -i %KEY% dojo/db_migrations/0250_executivereport.py %SERVER%:%REMOTE%/dojo/db_migrations/0250_executivereport.py

echo.
echo LISTO. En el servidor ejecuta:
echo   docker compose -f docker-compose.yml -f docker-compose.override.sqa.yml exec uwsgi python manage.py migrate
echo   docker compose -f docker-compose.yml -f docker-compose.override.sqa.yml restart uwsgi
