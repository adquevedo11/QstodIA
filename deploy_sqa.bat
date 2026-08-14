@echo off
set KEY=C:\Users\AndresFelipeQuevedoV\.ssh\devops.pem
set SERVER=azureuser@172.208.11.6
set REMOTE=~/defectdojo-sqa

echo ============================================================
echo  QustodIA - Deploy a produccion
echo  Servidor: %SERVER%
echo ============================================================

echo.
echo [1/4] CSS y estaticos...
scp -i %KEY% dojo/static/dojo/css/sqa-theme.css       %SERVER%:%REMOTE%/dojo/static/dojo/css/sqa-theme.css

echo [2/4] Templates base...
scp -i %KEY% dojo/templates/base.html                                         %SERVER%:%REMOTE%/dojo/templates/base.html
scp -i %KEY% dojo/templates/report_base.html                                  %SERVER%:%REMOTE%/dojo/templates/report_base.html
scp -i %KEY% dojo/templates/400.html                                          %SERVER%:%REMOTE%/dojo/templates/400.html
scp -i %KEY% dojo/templates/403.html                                          %SERVER%:%REMOTE%/dojo/templates/403.html
scp -i %KEY% dojo/templates/404.html                                          %SERVER%:%REMOTE%/dojo/templates/404.html
scp -i %KEY% dojo/templates/500.html                                          %SERVER%:%REMOTE%/dojo/templates/500.html
scp -i %KEY% dojo/templates/dojo/login.html                                   %SERVER%:%REMOTE%/dojo/templates/dojo/login.html
scp -i %KEY% dojo/templates/dojo/dashboard.html                               %SERVER%:%REMOTE%/dojo/templates/dojo/dashboard.html
scp -i %KEY% dojo/templates/dojo/finding_pdf_report.html                      %SERVER%:%REMOTE%/dojo/templates/dojo/finding_pdf_report.html
scp -i %KEY% dojo/templates/dojo/product.html                                 %SERVER%:%REMOTE%/dojo/templates/dojo/product.html
scp -i %KEY% dojo/templates/dojo/view_eng.html                                %SERVER%:%REMOTE%/dojo/templates/dojo/view_eng.html
scp -i %KEY% dojo/templates/dojo/view_product_details.html                    %SERVER%:%REMOTE%/dojo/templates/dojo/view_product_details.html

echo [3/4] Templates modulos SQA...
scp -i %KEY% dojo/templates/dojo/security_concept_form.html                   %SERVER%:%REMOTE%/dojo/templates/dojo/security_concept_form.html
scp -i %KEY% dojo/templates/dojo/security_concept_list.html                   %SERVER%:%REMOTE%/dojo/templates/dojo/security_concept_list.html
scp -i %KEY% dojo/templates/dojo/security_concept_report.html                 %SERVER%:%REMOTE%/dojo/templates/dojo/security_concept_report.html
scp -i %KEY% dojo/templates/dojo/executive_report_form.html                   %SERVER%:%REMOTE%/dojo/templates/dojo/executive_report_form.html
scp -i %KEY% dojo/templates/dojo/executive_report_list.html                   %SERVER%:%REMOTE%/dojo/templates/dojo/executive_report_list.html
scp -i %KEY% dojo/templates/dojo/executive_report_pdf.html                    %SERVER%:%REMOTE%/dojo/templates/dojo/executive_report_pdf.html
scp -i %KEY% dojo/templates/dojo/sqa_metrics.html                             %SERVER%:%REMOTE%/dojo/templates/dojo/sqa_metrics.html
scp -i %KEY% dojo/templates/dojo/go_live_readiness.html                       %SERVER%:%REMOTE%/dojo/templates/dojo/go_live_readiness.html
scp -i %KEY% dojo/templates/dojo/go_live_readiness_card.html                  %SERVER%:%REMOTE%/dojo/templates/dojo/go_live_readiness_card.html
scp -i %KEY% dojo/templates/dojo/go_live_readiness_content.html               %SERVER%:%REMOTE%/dojo/templates/dojo/go_live_readiness_content.html
scp -i %KEY% dojo/templates/dojo/pentest_list.html                            %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_list.html
scp -i %KEY% dojo/templates/dojo/pentest_form.html                            %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_form.html
scp -i %KEY% dojo/templates/dojo/pentest_form_standalone.html                 %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_form_standalone.html
scp -i %KEY% dojo/templates/dojo/pentest_detail.html                          %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_detail.html
scp -i %KEY% dojo/templates/dojo/pentest_finding_form.html                    %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_finding_form.html
scp -i %KEY% dojo/templates/dojo/pentest_finding_detail.html                  %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_finding_detail.html
scp -i %KEY% dojo/templates/dojo/pentest_report_form.html                     %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_report_form.html
scp -i %KEY% dojo/templates/dojo/pentest_report_pdf.html                      %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_report_pdf.html
scp -i %KEY% dojo/templates/dojo/pentest_type_list.html                       %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_type_list.html
scp -i %KEY% dojo/templates/dojo/pentest_confirm_delete.html                  %SERVER%:%REMOTE%/dojo/templates/dojo/pentest_confirm_delete.html
scp -i %KEY% dojo/templates/dojo/hour_pool_list.html                          %SERVER%:%REMOTE%/dojo/templates/dojo/hour_pool_list.html
scp -i %KEY% dojo/templates/dojo/hour_pool_form.html                          %SERVER%:%REMOTE%/dojo/templates/dojo/hour_pool_form.html
scp -i %KEY% dojo/templates/dojo/hour_pool_detail.html                        %SERVER%:%REMOTE%/dojo/templates/dojo/hour_pool_detail.html
scp -i %KEY% dojo/templates/dojo/hour_pool_report_pdf.html                    %SERVER%:%REMOTE%/dojo/templates/dojo/hour_pool_report_pdf.html
scp -i %KEY% dojo/templates/dojo/hour_pool_confirm_delete.html                %SERVER%:%REMOTE%/dojo/templates/dojo/hour_pool_confirm_delete.html
scp -i %KEY% dojo/templates/dojo/activity_type_list.html                      %SERVER%:%REMOTE%/dojo/templates/dojo/activity_type_list.html
scp -i %KEY% dojo/templates/dojo/time_entry_confirm_delete.html               %SERVER%:%REMOTE%/dojo/templates/dojo/time_entry_confirm_delete.html

echo [4/4] docker-compose override...
scp -i %KEY% docker-compose.override.sqa.yml  %SERVER%:%REMOTE%/docker-compose.override.sqa.yml

echo.
echo ============================================================
echo  LISTO. Ahora en el servidor ejecuta:
echo.
echo    ssh -i %KEY% %SERVER%
echo    cd defectdojo-sqa
echo    docker compose -f docker-compose.yml -f docker-compose.override.sqa.yml restart uwsgi nginx
echo ============================================================
