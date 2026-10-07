import copy
import logging
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count
from django.db.models.expressions import Case, When
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django_tagulous.models import TagField
from django_tagulous.models.managers import FakeTagRelatedManager  # noqa: F401 -- backward compat re-export

logger = logging.getLogger(__name__)
deduplicationLogger = logging.getLogger("dojo.specific-loggers.deduplication")

SEVERITY_CHOICES = (("Info", "Info"), ("Low", "Low"), ("Medium", "Medium"),
                    ("High", "High"), ("Critical", "Critical"))

SEVERITIES = [s[0] for s in SEVERITY_CHOICES]

EFFORT_FOR_FIXING_CHOICES = (("", ""), ("Low", "Low"), ("Medium", "Medium"), ("High", "High"))

# fields returned in statistics, typically all status fields
STATS_FIELDS = ["active", "verified", "duplicate", "false_p", "out_of_scope", "is_mitigated", "risk_accepted", "total"]
# default template with all values set to 0
DEFAULT_STATS = {sev.lower(): dict.fromkeys(STATS_FIELDS, 0) for sev in SEVERITIES}


def _get_annotations_for_statistics():
    annotations = {stats_field.lower(): Count(Case(When(**{stats_field: True}, then=1))) for stats_field in STATS_FIELDS if stats_field != "total"}
    # add total
    annotations["total"] = Count("id")
    return annotations


def _get_statistics_for_queryset(qs, annotation_factory):
    # order by to get rid of default ordering that would mess with group_by
    # group by severity (lowercase)
    values = qs.annotate(sev=Lower("severity")).values("sev").order_by()
    # add annotation for each status field
    values = values.annotate(**annotation_factory())
    # make sure sev and total are included
    stat_fields = ["sev", "total", *STATS_FIELDS]
    # go for it
    values = values.values(*stat_fields)

    # not sure if there's a smarter way to convert a list of dicts into a dict of dicts
    # need to copy the DEFAULT_STATS otherwise it gets overwritten
    stats = copy.copy(DEFAULT_STATS)
    for row in values:
        sev = row.pop("sev")
        stats[sev] = row

    values_total = qs.values()
    values_total = values_total.aggregate(**annotation_factory())
    stats["total"] = values_total
    return stats


def _sync_inherited_tags(obj, incoming_inherited_tags):
    # Backward-compat shim. Implementation lives in dojo.tags.inheritance; lazy
    # import keeps dojo.models loadable before dojo.tags.inheritance (which
    # transitively imports dojo.utils -> dojo.models) is ready.
    from dojo.tags.inheritance import _sync_inherited_tags as _impl  # noqa: PLC0415
    return _impl(obj, incoming_inherited_tags)


def copy_model_util(model_in_database, exclude_fields: list[str] | None = None):
    if exclude_fields is None:
        exclude_fields = []
    new_model_instance = model_in_database.__class__()
    for field in model_in_database._meta.fields:
        if field.name not in {"id", *exclude_fields}:
            setattr(new_model_instance, field.name, getattr(model_in_database, field.name))
    return new_model_instance


def tomorrow():
    """Returns a date representing the day after today."""
    return timezone.now().date() + timedelta(days=1)


@deconstructible
class UniqueUploadNameProvider:

    """
    A callable to be passed as upload_to parameter to FileField.

    Uploaded files will get random names based on UUIDs inside the given directory;
    strftime-style formatting is supported within the directory path. If keep_basename
    is True, the original file name is prepended to the UUID. If keep_ext is disabled,
    the filename extension will be dropped.
    """

    def __init__(self, directory=None, *, keep_basename=False, keep_ext=True):
        self.directory = directory
        self.keep_basename = keep_basename
        self.keep_ext = keep_ext

    def __call__(self, model_instance, filename):
        path = Path(filename)
        base = path.parent / path.stem
        ext = path.suffix
        filename = f"{base}_{uuid4()}" if self.keep_basename else str(uuid4())
        if self.keep_ext:
            filename += ext
        if self.directory is None:
            return filename
        return Path(now().strftime(self.directory)) / filename


User = get_user_model()


from dojo.regulations.models import Regulation  # noqa: E402, F401, I001 -- re-export; user/system_settings block intentionally out-of-order (load-order)
from dojo.user.models import (  # noqa: E402, F401 -- must precede system_settings (middleware load-order)
    DEDUPLICATION_EXECUTION_MODE_ASYNC,
    DEDUPLICATION_EXECUTION_MODE_ASYNC_WAIT,
    DEDUPLICATION_EXECUTION_MODE_CHOICES,
    DEDUPLICATION_EXECUTION_MODE_SYNC,
    DEDUPLICATION_EXECUTION_MODES,
    Contact,
    Dojo_User,
    UserContactInfo,
)
from dojo.system_settings.models import System_Settings  # noqa: E402, F401 -- re-export


def get_current_date():
    return timezone.now().date()


def get_current_datetime():
    return timezone.now()


from dojo.cicd_infrastructure.models import CICDInfrastructure  # noqa: E402, F401 -- re-export
from dojo.file_uploads.models import FileAccessToken, FileUpload  # noqa: E402, F401 -- re-export
from dojo.note_type.models import Note_Type  # noqa: E402, F401 -- re-export
from dojo.notes.models import (  # noqa: E402, F401 -- re-export; Notes used by Risk_Acceptance.notes M2M below
    NoteHistory,
    Notes,
)
from dojo.product.models import (  # noqa: E402 -- re-export; class-body FKs below reference these
    Product,
    Product_API_Scan_Configuration,  # noqa: F401 -- re-export
    Product_Line,  # noqa: F401 -- re-export
)
from dojo.product_type.models import Product_Type  # noqa: E402, F401 -- re-export
from dojo.reports.models import Report_Type  # noqa: E402, F401 -- re-export
from dojo.test.models import (  # noqa: E402 -- re-export; class-body FKs below reference these
    IMPORT_ACTIONS,  # noqa: F401 -- re-export
    IMPORT_CLOSED_FINDING,  # noqa: F401 -- re-export
    IMPORT_CREATED_FINDING,  # noqa: F401 -- re-export
    IMPORT_REACTIVATED_FINDING,  # noqa: F401 -- re-export
    IMPORT_UNTOUCHED_FINDING,  # noqa: F401 -- re-export
    Test,
    Test_Import,  # noqa: F401 -- re-export
    Test_Import_Finding_Action,  # noqa: F401 -- re-export
    Test_Type,  # noqa: F401 -- re-export
)


class DojoMeta(models.Model):
    name = models.CharField(max_length=120)
    value = models.CharField(max_length=300)
    product = models.ForeignKey("Product",
                                on_delete=models.CASCADE,
                                null=True,
                                editable=False,
                                related_name="product_meta")
    endpoint = models.ForeignKey("Endpoint",
                                 on_delete=models.CASCADE,
                                 null=True,
                                 editable=False,
                                 related_name="endpoint_meta")
    finding = models.ForeignKey("Finding",
                                 on_delete=models.CASCADE,
                                 null=True,
                                 editable=False,
                                 related_name="finding_meta")
    location = models.ForeignKey("Location",
                                 on_delete=models.CASCADE,
                                 null=True,
                                 editable=False,
                                 related_name="location_meta")
    # Scopes location metadata per product, since a Location row is shared by every product
    # that references it. Not a parent relation, so clean() below does not count it.
    location_product = models.ForeignKey("Product",
                                 on_delete=models.CASCADE,
                                 null=True,
                                 editable=False,
                                 related_name="location_meta_scope")

    class Meta:
        unique_together = (("product", "name"),
                           ("endpoint", "name"),
                           ("finding", "name"),
                           ("location", "location_product", "name"))

    def __str__(self):
        return f"{self.name}: {self.value}"

    """
    Verify that this metadata entry belongs only to one object.
    """
    def clean(self):

        ids = [self.product_id,
               self.endpoint_id,
               self.finding_id,
               self.location_id]
        ids_count = 0

        for obj_id in ids:
            if obj_id is not None:
                ids_count += 1

        if ids_count == 0:
            msg = "Metadata entries need either a product, endpoint, location or a finding"
            raise ValidationError(msg)
        if ids_count > 1:
            msg = "Metadata entries may not have more than one relation, either a product, endpoint, location or a finding"
            raise ValidationError(msg)


class SLA_Configuration(models.Model):
    name = models.CharField(max_length=128, unique=True, blank=False, verbose_name=_("Custom SLA Name"),
        help_text=_("A unique name for the set of SLAs."))
    description = models.CharField(
        max_length=512,
        null=True,
        blank=True)
    critical = models.IntegerField(
        default=7,
        verbose_name=_("Critical Finding SLA Days"),
        help_text=_("The number of days to remediate a critical finding."))
    enforce_critical = models.BooleanField(
        default=True,
        verbose_name=_("Enforce Critical Finding SLA Days"),
        help_text=_("When enabled, critical findings will be assigned an SLA expiration date based on the critical finding SLA days within this SLA configuration."))
    high = models.IntegerField(
        default=30,
        verbose_name=_("High Finding SLA Days"),
        help_text=_("The number of days to remediate a high finding."))
    enforce_high = models.BooleanField(
        default=True,
        verbose_name=_("Enforce High Finding SLA Days"),
        help_text=_("When enabled, high findings will be assigned an SLA expiration date based on the high finding SLA days within this SLA configuration."))
    medium = models.IntegerField(
        default=90,
        verbose_name=_("Medium Finding SLA Days"),
        help_text=_("The number of days to remediate a medium finding."))
    enforce_medium = models.BooleanField(
        default=True,
        verbose_name=_("Enforce Medium Finding SLA Days"),
        help_text=_("When enabled, medium findings will be assigned an SLA expiration date based on the medium finding SLA days within this SLA configuration."))
    low = models.IntegerField(
        default=120,
        verbose_name=_("Low Finding SLA Days"),
        help_text=_("The number of days to remediate a low finding."))
    enforce_low = models.BooleanField(
        default=True,
        verbose_name=_("Enforce Low Finding SLA Days"),
        help_text=_("When enabled, low findings will be assigned an SLA expiration date based on the low finding SLA days within this SLA configuration."))
    restart_sla_on_reactivation = models.BooleanField(
        default=False,
        verbose_name=_("Restart SLA when findings are reactivated"),
        help_text=_("When enabled, findings that were previously mitigated but are reactivated durign reimport will have their SLA period restarted."))
    async_updating = models.BooleanField(
        default=False,
        help_text=_("Findings under this SLA configuration are asynchronously being updated"))

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # get the initial sla config before saving (if this is an existing sla config)
        initial_sla_config = None
        if self.pk is not None:
            initial_sla_config = SLA_Configuration.objects.get(pk=self.pk)
            # if initial config exists and async finding update is already running, revert sla config before saving
            if initial_sla_config and self.async_updating:
                self.critical = initial_sla_config.critical
                self.enforce_critical = initial_sla_config.enforce_critical
                self.high = initial_sla_config.high
                self.enforce_high = initial_sla_config.enforce_high
                self.medium = initial_sla_config.medium
                self.enforce_medium = initial_sla_config.enforce_medium
                self.low = initial_sla_config.low
                self.enforce_low = initial_sla_config.enforce_low

        super().save(*args, **kwargs)

        # if the initial sla config exists and async finding update is not running
        if initial_sla_config is not None and not self.async_updating:
            # check which sla days fields changed based on severity
            severities = []
            if (initial_sla_config.critical != self.critical) or (initial_sla_config.enforce_critical != self.enforce_critical):
                severities.append("Critical")
            if (initial_sla_config.high != self.high) or (initial_sla_config.enforce_high != self.enforce_high):
                severities.append("High")
            if (initial_sla_config.medium != self.medium) or (initial_sla_config.enforce_medium != self.enforce_medium):
                severities.append("Medium")
            if (initial_sla_config.low != self.low) or (initial_sla_config.enforce_low != self.enforce_low):
                severities.append("Low")
            # if severities have changed, update finding sla expiration dates with those severities
            if severities:
                # set the async updating flag to true for this sla config
                self.async_updating = True
                super().save(*args, **kwargs)
                # set the async updating flag to true for all products using this sla config
                products = Product.objects.filter(sla_configuration=self)
                for product in products:
                    product.async_updating = True
                    super(Product, product).save()
                # launch the async task to update all finding sla expiration dates
                from dojo.sla_config.helpers import async_update_sla_expiration_dates_sla_config_sync  # noqa: I001, PLC0415 circular import
                from dojo.celery_dispatch import dojo_dispatch_task  # noqa: PLC0415 circular import

                dojo_dispatch_task(
                    async_update_sla_expiration_dates_sla_config_sync,
                    self.id,
                    list(products.values_list("id", flat=True)),
                    severities=severities,
                )
                # The async task refetches and resets async_updating on its own copy.
                # Mirror that on this in-memory instance so a subsequent save() on the
                # same instance does not trigger the lock-revert path at line 1058.
                self.async_updating = False

    def clean(self):
        sla_days = [self.critical, self.high, self.medium, self.low]

        for sla_day in sla_days:
            if sla_day < 1:
                msg = "SLA Days must be at least 1"
                raise ValidationError(msg)

    def delete(self, *args, **kwargs):
        logger.debug("%d sla configuration delete", self.id)

        if self.id != 1:
            super().delete(*args, **kwargs)
        else:
            msg = "Unable to delete default SLA Configuration"
            raise ValidationError(msg)

    def get_summary(self):
        return f"{self.name} - Critical: {self.critical}, High: {self.high}, Medium: {self.medium}, Low: {self.low}"


from dojo.tool_config.models import Tool_Configuration  # noqa: E402, F401 -- re-export
from dojo.tool_type.models import Tool_Type  # noqa: E402, F401 -- re-export


class Network_Locations(models.Model):
    location = models.CharField(max_length=500, help_text=_("Location of network testing: Examples: VPN, Internet or Internal."))

    def __str__(self):
        return self.location


from dojo.development_environment.models import Development_Environment  # noqa: E402, F401 -- re-export
from dojo.endpoint.models import Endpoint, Endpoint_Params, Endpoint_Status  # noqa: E402, F401 -- re-export
from dojo.engagement.models import (  # noqa: E402 -- re-export; class-body FKs below reference these
    ENGAGEMENT_STATUS_CHOICES,  # noqa: F401 -- re-export
    Engagement,
    Engagement_Presets,  # noqa: F401 -- re-export
)
from dojo.product_attributes.models import (  # noqa: E402, F401 -- re-export; Product FKs below reference these
    Product_Lifecycle,
    Product_Origin,
    Product_Platform,
)


class Sonarqube_Issue(models.Model):
    key = models.CharField(max_length=60, unique=True, help_text=_("SonarQube issue key"))
    status = models.CharField(max_length=20, help_text=_("SonarQube issue status"))
    type = models.CharField(max_length=20, help_text=_("SonarQube issue type"))

    def __str__(self):
        return self.key


class Sonarqube_Issue_Transition(models.Model):
    sonarqube_issue = models.ForeignKey(Sonarqube_Issue, on_delete=models.CASCADE, db_index=True)
    created = models.DateTimeField(auto_now_add=True, null=False)
    finding_status = models.CharField(max_length=100)
    sonarqube_status = models.CharField(max_length=50)
    transitions = models.CharField(max_length=100)

    class Meta:
        ordering = ("-created", )


from dojo.finding.models import (  # noqa: E402 -- re-export; class-body FKs below reference these
    CWE,  # noqa: F401 -- re-export
    BurpRawRequestResponse,  # noqa: F401 -- re-export
    Finding,
    Finding_CWE,  # noqa: F401 -- re-export
    Finding_Group,  # noqa: F401 -- re-export
    Finding_Template,
    Vulnerability_Id,  # noqa: F401 -- re-export (legacy; retained for a transition period, see model)
)
from dojo.vulnerability.models import (  # noqa: E402 -- re-export; FKs reference dojo.Finding / dojo.Vulnerability by string
    FindingVulnerabilityReference,  # noqa: F401 -- re-export
    Vulnerability,  # noqa: F401 -- re-export
)


class Check_List(models.Model):
    session_management = models.CharField(max_length=50, default="none")
    session_issues = models.ManyToManyField(Finding,
                                            related_name="session_issues",
                                            blank=True)
    encryption_crypto = models.CharField(max_length=50, default="none")
    crypto_issues = models.ManyToManyField(Finding,
                                           related_name="crypto_issues",
                                           blank=True)
    configuration_management = models.CharField(max_length=50, default="")
    config_issues = models.ManyToManyField(Finding,
                                           related_name="config_issues",
                                           blank=True)
    authentication = models.CharField(max_length=50, default="none")
    auth_issues = models.ManyToManyField(Finding,
                                         related_name="auth_issues",
                                         blank=True)
    authorization_and_access_control = models.CharField(max_length=50,
                                                        default="none")
    author_issues = models.ManyToManyField(Finding,
                                           related_name="author_issues",
                                           blank=True)
    data_input_sanitization_validation = models.CharField(max_length=50,
                                                          default="none")
    data_issues = models.ManyToManyField(Finding, related_name="data_issues",
                                         blank=True)
    sensitive_data = models.CharField(max_length=50, default="none")
    sensitive_issues = models.ManyToManyField(Finding,
                                              related_name="sensitive_issues",
                                              blank=True)
    other = models.CharField(max_length=50, default="none")
    other_issues = models.ManyToManyField(Finding, related_name="other_issues",
                                          blank=True)
    engagement = models.ForeignKey(Engagement, editable=False,
                                   related_name="eng_for_check", on_delete=models.CASCADE)

    @staticmethod
    def get_status(pass_fail):
        if pass_fail == "Pass":  # noqa: S105
            return "success"
        if pass_fail == "Fail":  # noqa: S105
            return "danger"
        return "warning"

    def get_breadcrumb(self):
        bc = self.engagement.get_breadcrumb()
        bc += [{"title": "Check List",
                "url": reverse("complete_checklist",
                               args=(self.engagement.id,))}]
        return bc


from dojo.announcement.models import (  # noqa: E402 -- re-export
    ANNOUNCEMENT_STYLE_CHOICES,  # noqa: F401 -- re-export
    Announcement,  # noqa: F401 -- re-export
    UserAnnouncement,  # noqa: F401 -- re-export
)
from dojo.banner.models import BannerConf  # noqa: E402, F401 -- re-export
from dojo.github.models import (  # noqa: E402, F401 -- backward compat
    GITHUB_Clone,
    GITHUB_Conf,
    GITHUB_Details_Cache,
    GITHUB_Issue,
    GITHUB_PKey,
)
from dojo.jira.models import (  # noqa: E402,F401 backward compat
    JIRA_Instance,
    JIRA_Instance_Admin,
    JIRA_Issue,
    JIRA_Project,
)
from dojo.notifications.admin import NotificationsAdmin  # noqa: E402, F401  -- backward compat
from dojo.notifications.models import (  # noqa: E402, F401  -- backward compat
    DEFAULT_NOTIFICATION,
    NOTIFICATION_CHOICE_ALERT,
    NOTIFICATION_CHOICE_MAIL,
    NOTIFICATION_CHOICE_MSTEAMS,
    NOTIFICATION_CHOICE_SLACK,
    NOTIFICATION_CHOICE_WEBHOOKS,
    NOTIFICATION_CHOICES,
    Alerts,
    Notification_Webhooks,
    Notifications,
)
from dojo.risk_acceptance.models import Risk_Acceptance  # noqa: E402, F401 -- re-export
from dojo.tool_product.models import Tool_Product_History, Tool_Product_Settings  # noqa: E402, F401 -- re-export


class Language_Type(models.Model):
    language = models.CharField(max_length=100, null=False, unique=True)
    color = models.CharField(max_length=7, null=True, blank=True, verbose_name=_("HTML color"))

    def __str__(self):
        return self.language


class Languages(models.Model):
    language = models.ForeignKey(Language_Type, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Dojo_User, editable=True, blank=True, null=True, on_delete=models.RESTRICT)
    files = models.IntegerField(blank=True, null=True, verbose_name=_("Number of files"))
    blank = models.IntegerField(blank=True, null=True, verbose_name=_("Number of blank lines"))
    comment = models.IntegerField(blank=True, null=True, verbose_name=_("Number of comment lines"))
    code = models.IntegerField(blank=True, null=True, verbose_name=_("Number of code lines"))
    created = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        unique_together = [("language", "product")]

    def __str__(self):
        return self.language.language


class App_Analysis(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, null=False)
    user = models.ForeignKey(Dojo_User, editable=True, on_delete=models.RESTRICT)
    confidence = models.IntegerField(blank=True, null=True, verbose_name=_("Confidence level"))
    version = models.CharField(max_length=200, null=True, blank=True, verbose_name=_("Version Number"))
    icon = models.CharField(max_length=200, null=True, blank=True)
    website = models.URLField(max_length=400, null=True, blank=True)
    website_found = models.URLField(max_length=400, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=False)

    tags = TagField(blank=True, force_lowercase=True)

    class Meta:
        indexes = [
            # Global search (pro/search/): weighted tsvector FTS + trigram fuzzy match.
            GinIndex(
                SearchVector("name", weight="A", config="english"),
                name="dojo_app_analysis_fts_gin",
            ),
            GinIndex(fields=["name"], opclasses=["gin_trgm_ops"], name="dojo_app_analysis_name_trgm"),
        ]

    def __str__(self):
        return self.name + " | " + self.product.name


from dojo.object.models import Objects_Product, Objects_Review  # noqa: E402, F401 -- re-export


class Testing_Guide_Category(models.Model):
    name = models.CharField(max_length=300)
    created = models.DateTimeField(auto_now_add=True, null=False)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Testing_Guide(models.Model):
    testing_guide_category = models.ForeignKey(Testing_Guide_Category, on_delete=models.CASCADE)
    identifier = models.CharField(max_length=20, blank=True, null=True, help_text=_("Test Unique Identifier"))
    name = models.CharField(max_length=400, help_text=_("Name of the test"))
    summary = models.CharField(max_length=800, help_text=_("Summary of the test"))
    objective = models.CharField(max_length=800, help_text=_("Objective of the test"))
    how_to_test = models.TextField(default=None, help_text=_("How to test the objective"))
    results_expected = models.CharField(max_length=800, help_text=_("What the results look like for a test"))
    created = models.DateTimeField(auto_now_add=True, null=False)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.testing_guide_category.name + ": " + self.name


from dojo.benchmark.models import (  # noqa: E402, I001 -- re-export; backward compat
    Benchmark_Category,  # noqa: F401
    Benchmark_Product,  # noqa: F401
    Benchmark_Product_Summary,  # noqa: F401
    Benchmark_Requirement,  # noqa: F401
    Benchmark_Type,  # noqa: F401
)
from dojo.survey.models import (  # noqa: E402 -- re-export; backward compat
    Answer,  # noqa: F401
    Answered_Survey,  # noqa: F401
    Choice,  # noqa: F401
    ChoiceAnswer,  # noqa: F401
    ChoiceQuestion,  # noqa: F401
    Engagement_Survey,  # noqa: F401
    General_Survey,  # noqa: F401
    Question,  # noqa: F401
    TextAnswer,  # noqa: F401
    TextQuestion,  # noqa: F401
    default_expiration,  # noqa: F401
)

# Audit logging registration is now handled in auditlog.py and configured in apps.py
# This allows for conditional registration of either django-auditlog or django-pghistory
# The audit system is configured in DojoAppConfig.ready() to ensure all models are loaded


from dojo.utils import (  # noqa: E402
    parse_cvss_data,  # noqa: F401 -- backward compat re-export; side-effect loads dojo.utils → dojo.location models
)

admin.site.register(Product.tags.tag_model)
admin.site.register(Test.tags.tag_model)
admin.site.register(Test.inherited_tags.tag_model)
admin.site.register(Finding.tags.tag_model)
admin.site.register(Finding.inherited_tags.tag_model)
admin.site.register(Engagement.tags.tag_model)
admin.site.register(Engagement.inherited_tags.tag_model)
admin.site.register(Finding_Template.tags.tag_model)
admin.site.register(App_Analysis.tags.tag_model)
# Objects_Product.tags registered in dojo/object/admin.py

# Testing
admin.site.register(Testing_Guide_Category)
admin.site.register(Testing_Guide)

admin.site.register(Network_Locations)
# Objects_Product + Objects_Review admin registered in dojo/object/admin.py
admin.site.register(Languages)
admin.site.register(Language_Type)
admin.site.register(App_Analysis)
# FileUpload + FileAccessToken admin registered in dojo/file_uploads/admin.py
admin.site.register(Check_List)
# Notes + NoteHistory admin registered in dojo/notes/admin.py
# Note_Type admin registered in dojo/note_type/admin.py
admin.site.register(SLA_Configuration)
# Regulation admin registered in dojo/regulations/admin.py
from dojo.authorization.models import (  # noqa: E402
    Dojo_Group,
    Dojo_Group_Member,
    Global_Role,
    Product_Group,
    Product_Member,
    Product_Type_Group,
    Product_Type_Member,
    Role,
)

admin.site.register(Global_Role)
admin.site.register(Role)
admin.site.register(Dojo_Group)

# SonarQube Integration
admin.site.register(Sonarqube_Issue)
admin.site.register(Sonarqube_Issue_Transition)

admin.site.register(Dojo_Group_Member)
admin.site.register(Product_Member)
admin.site.register(Product_Group)
admin.site.register(Product_Type_Member)
admin.site.register(Product_Type_Group)

# NoteHistory admin registered in dojo/notes/admin.py
# Report_Type admin registered in dojo/reports/admin.py
admin.site.register(DojoMeta)
# Development_Environment admin registered in dojo/development_environment/admin.py
# Announcement + UserAnnouncement admin registered in dojo/announcement/admin.py
# BannerConf admin registered in dojo/banner/admin.py

# ═══════════════════════════════════════════════════════════════════════════════
#  QustodIA — Custom Models (SQA SA · CQASA)
# ═══════════════════════════════════════════════════════════════════════════════

# ── Concepto de Seguridad ─────────────────────────────────────────────────────

RISK_LEVEL_CHOICES = [
    ("Crítico",   "Crítico"),
    ("Alto",      "Alto"),
    ("Medio",     "Medio"),
    ("Bajo",      "Bajo"),
    ("Aceptable", "Aceptable"),
]


class SecurityConcept(models.Model):
    reference     = models.CharField(max_length=100, blank=True, verbose_name="Referencia")
    title         = models.CharField(max_length=500, verbose_name="Título")
    client        = models.CharField(max_length=300, blank=True, verbose_name="Cliente")
    scope         = models.CharField(max_length=500, blank=True, verbose_name="Alcance")
    context_text  = models.TextField(blank=True, verbose_name="Contexto")
    analysis      = models.TextField(blank=True, verbose_name="Análisis")
    risk_level    = models.CharField(max_length=50, choices=RISK_LEVEL_CHOICES, default="Medio", verbose_name="Nivel de riesgo")
    conclusion    = models.TextField(blank=True, verbose_name="Conclusión")
    analyst_name  = models.CharField(max_length=300, blank=True, verbose_name="Analista")
    analyst_title = models.CharField(max_length=300, blank=True, verbose_name="Cargo")
    findings      = models.ManyToManyField("Finding", blank=True, related_name="security_concepts", verbose_name="Hallazgos")
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    created_by    = models.ForeignKey(
        Dojo_User, null=True, blank=True, on_delete=models.SET_NULL, related_name="security_concepts",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Concepto de Seguridad"
        verbose_name_plural = "Conceptos de Seguridad"

    def __str__(self):
        return f"{self.reference} — {self.title}" if self.reference else self.title


# ── Informe Ejecutivo ─────────────────────────────────────────────────────────

EXEC_REPORT_CLASSIFICATION = [
    ('Confidencial', 'Confidencial'),
    ('Interno', 'Interno'),
    ('Público', 'Público'),
]


class ExecutiveReport(models.Model):
    product           = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='executive_reports')
    engagements       = models.ManyToManyField('Engagement', blank=True, related_name='executive_reports')
    title             = models.CharField(max_length=500)
    period_start      = models.DateField()
    period_end        = models.DateField()
    classification    = models.CharField(max_length=50, choices=EXEC_REPORT_CLASSIFICATION, default='Confidencial')
    analyst_name      = models.CharField(max_length=300, blank=True)
    analyst_title     = models.CharField(max_length=300, blank=True)
    executive_summary = models.TextField(blank=True)
    recommendations   = models.TextField(blank=True)
    next_steps        = models.TextField(blank=True)
    conclusion        = models.TextField(blank=True)
    sections          = models.JSONField(default=dict)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    created_by        = models.ForeignKey(
        Dojo_User, null=True, blank=True, on_delete=models.SET_NULL, related_name='executive_reports',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Informe Ejecutivo'
        verbose_name_plural = 'Informes Ejecutivos'

    def __str__(self):
        return f"{self.title} — {self.product.name}"


# ── Pentest Module ────────────────────────────────────────────────────────────

class PentestType(models.Model):
    name        = models.CharField(max_length=100, unique=True, verbose_name="Tipo")
    description = models.TextField(blank=True, verbose_name="Descripción")
    is_active   = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        ordering = ['name']
        verbose_name = "Tipo de Pentest"
        verbose_name_plural = "Tipos de Pentest"

    def __str__(self):
        return self.name


class PentestProject(models.Model):
    STATUS_CHOICES = [
        ('planned',     'Planificado'),
        ('in_progress', 'En progreso'),
        ('completed',   'Completado'),
        ('delivered',   'Entregado'),
    ]
    INDUSTRY_CHOICES = [
        ('banca',             'Banca y Financiero'),
        ('fintech',           'Fintech'),
        ('seguros',           'Seguros'),
        ('salud',             'Salud'),
        ('gobierno',          'Gobierno y Sector Público'),
        ('retail',            'Retail y E-commerce'),
        ('tecnologia',        'Tecnología'),
        ('educacion',         'Educación'),
        ('energia',           'Energía y Utilities'),
        ('manufactura',       'Manufactura e Industria'),
        ('telecomunicaciones','Telecomunicaciones'),
        ('otro',              'Otro'),
    ]

    engagement   = models.ForeignKey('Engagement', on_delete=models.CASCADE, related_name='pentest_projects')
    title        = models.CharField(max_length=200, verbose_name="Título")
    pentest_type = models.ForeignKey(PentestType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo")
    industry     = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, blank=True, verbose_name="Sector/Industria del cliente")
    methodology  = models.CharField(max_length=200, blank=True, verbose_name="Metodología")
    scope        = models.TextField(blank=True, verbose_name="Alcance")
    objectives   = models.TextField(blank=True, verbose_name="Objetivos")
    start_date   = models.DateField(null=True, blank=True, verbose_name="Fecha inicio")
    end_date     = models.DateField(null=True, blank=True, verbose_name="Fecha fin")
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name="Estado")
    lead_analyst = models.ForeignKey(Dojo_User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_pentests', verbose_name="Analista líder")
    analysts     = models.ManyToManyField(Dojo_User, blank=True, related_name='assigned_pentests', verbose_name="Equipo")
    created_by   = models.ForeignKey(Dojo_User, on_delete=models.SET_NULL, null=True, related_name='created_pentests')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Proyecto Pentest"
        verbose_name_plural = "Proyectos Pentest"

    def __str__(self):
        return f"{self.title} — {self.engagement}"

    def get_severity_summary(self):
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'informational': 0}
        for f in self.pentest_findings.all():
            if f.severity in counts:
                counts[f.severity] += 1
        return counts


class PentestFinding(models.Model):
    STATUS_CHOICES = [
        ('identified', 'Identificado'),
        ('confirmed',  'Confirmado'),
        ('exploited',  'Explotado'),
        ('reported',   'Reportado'),
    ]
    SEVERITY_CHOICES = [
        ('critical',      'Crítico'),
        ('high',          'Alto'),
        ('medium',        'Medio'),
        ('low',           'Bajo'),
        ('informational', 'Informativo'),
    ]

    project            = models.ForeignKey(PentestProject, on_delete=models.CASCADE, related_name='pentest_findings')
    title              = models.CharField(max_length=300, verbose_name="Título")
    description        = models.TextField(verbose_name="Descripción técnica")
    steps_to_reproduce = models.TextField(blank=True, verbose_name="Pasos para reproducir")
    impact             = models.TextField(blank=True, verbose_name="Impacto")
    affected_component = models.CharField(max_length=500, blank=True, verbose_name="Componente afectado")
    cvss_score         = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name="CVSS Score")
    cvss_vector        = models.CharField(max_length=200, blank=True, verbose_name="CVSS Vector")
    severity           = models.CharField(max_length=20, choices=SEVERITY_CHOICES, blank=True, verbose_name="Severidad")
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='identified', verbose_name="Estado")
    remediation        = models.TextField(blank=True, verbose_name="Remediación")
    references         = models.TextField(blank=True, verbose_name="Referencias")
    order              = models.IntegerField(default=0, verbose_name="Orden")
    created_by         = models.ForeignKey(Dojo_User, on_delete=models.SET_NULL, null=True, related_name='pentest_findings')
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-cvss_score']
        verbose_name = "Hallazgo Pentest"
        verbose_name_plural = "Hallazgos Pentest"

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"

    def save(self, *args, **kwargs):
        if self.cvss_score is not None:
            score = float(self.cvss_score)
            if score >= 9.0:
                self.severity = 'critical'
            elif score >= 7.0:
                self.severity = 'high'
            elif score >= 4.0:
                self.severity = 'medium'
            elif score > 0:
                self.severity = 'low'
            else:
                self.severity = 'informational'
        super().save(*args, **kwargs)

    @property
    def severity_color(self):
        return {
            'critical': '#c0392b', 'high': '#e67e22',
            'medium': '#d4ac0d',   'low': '#2980b9',
            'informational': '#7f8c8d',
        }.get(self.severity, '#7f8c8d')


class PentestEvidence(models.Model):
    FILE_TYPE_CHOICES = [
        ('screenshot', 'Captura de pantalla'),
        ('payload',    'Payload'),
        ('log',        'Log'),
        ('script',     'Script'),
        ('other',      'Otro'),
    ]

    finding     = models.ForeignKey(PentestFinding, on_delete=models.CASCADE, related_name='evidences')
    title       = models.CharField(max_length=200, verbose_name="Título")
    caption     = models.TextField(blank=True, verbose_name="Descripción")
    file        = models.FileField(upload_to='pentest_evidence/%Y/%m/', verbose_name="Archivo")
    file_type   = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='screenshot', verbose_name="Tipo")
    uploaded_by = models.ForeignKey(Dojo_User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"

    def __str__(self):
        return f"{self.title} — {self.finding.title}"

    @property
    def is_image(self):
        name = self.file.name.lower() if self.file else ''
        return any(name.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp'])


class PentestReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('executive', 'Ejecutivo'),
        ('technical', 'Técnico'),
    ]
    STATUS_CHOICES = [
        ('draft',     'Borrador'),
        ('final',     'Final'),
        ('delivered', 'Entregado'),
    ]

    project           = models.ForeignKey(PentestProject, on_delete=models.CASCADE, related_name='reports')
    report_type       = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name="Tipo de reporte")
    version           = models.CharField(max_length=10, default='1.0', verbose_name="Versión")
    executive_summary = models.TextField(blank=True, verbose_name="Resumen ejecutivo")
    conclusions       = models.TextField(blank=True, verbose_name="Conclusiones")
    recommendations   = models.TextField(blank=True, verbose_name="Recomendaciones")
    generated_pdf     = models.FileField(upload_to='pentest_reports/%Y/%m/', null=True, blank=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Estado")
    generated_by      = models.ForeignKey(Dojo_User, on_delete=models.SET_NULL, null=True, related_name='pentest_reports')
    generated_at      = models.DateTimeField(auto_now_add=True)
    delivered_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Reporte Pentest"
        verbose_name_plural = "Reportes Pentest"

    def __str__(self):
        return f"{self.get_report_type_display()} v{self.version} — {self.project.title}"


# ── Hour Pool Module ──────────────────────────────────────────────────────────

class ActivityType(models.Model):
    name        = models.CharField(max_length=100, unique=True, verbose_name="Actividad")
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Tipo de Actividad"
        verbose_name_plural = "Tipos de Actividad"

    def __str__(self):
        return self.name


class HourPool(models.Model):
    STATUS_CHOICES = [
        ('active',    'Activa'),
        ('depleted',  'Agotada'),
        ('expired',   'Vencida'),
        ('cancelled', 'Cancelada'),
    ]

    product             = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='hour_pools')
    name                = models.CharField(max_length=200, verbose_name="Nombre de la bolsa")
    total_hours         = models.PositiveIntegerField(verbose_name="Horas totales")
    alert_threshold_pct = models.PositiveIntegerField(default=20, verbose_name="Alerta al % restante")
    valid_from          = models.DateField(verbose_name="Válida desde")
    valid_until         = models.DateField(null=True, blank=True, verbose_name="Válida hasta")
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Estado")
    notes               = models.TextField(blank=True, verbose_name="Notas")
    created_by          = models.ForeignKey(Dojo_User, on_delete=models.SET_NULL, null=True, related_name='created_hour_pools')
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bolsa de Horas"
        verbose_name_plural = "Bolsas de Horas"

    def __str__(self):
        return f"{self.name} — {self.product.name}"

    @property
    def used_hours(self):
        from django.db.models import Sum
        result = self.time_entries.aggregate(total=Sum('hours'))['total']
        return result or 0

    @property
    def remaining_hours(self):
        return self.total_hours - self.used_hours

    @property
    def consumption_pct(self):
        if self.total_hours == 0:
            return 0
        return round((self.used_hours / self.total_hours) * 100, 1)

    @property
    def is_alert(self):
        threshold = self.total_hours * self.alert_threshold_pct / 100
        return self.remaining_hours <= threshold

    @property
    def status_color(self):
        if self.status == 'active':
            return '#27ae60' if not self.is_alert else '#e67e22'
        return {'depleted': '#c0392b', 'expired': '#7f8c8d', 'cancelled': '#bdc3c7'}.get(self.status, '#7f8c8d')


class TimeEntry(models.Model):
    pool            = models.ForeignKey(HourPool, on_delete=models.CASCADE, related_name='time_entries')
    pentest_project = models.ForeignKey(PentestProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries')
    analyst         = models.ForeignKey(Dojo_User, on_delete=models.SET_NULL, null=True, related_name='time_entries')
    date            = models.DateField(verbose_name="Fecha")
    hours           = models.PositiveIntegerField(verbose_name="Horas")
    activity_type   = models.ForeignKey(ActivityType, on_delete=models.SET_NULL, null=True, verbose_name="Actividad")
    description     = models.TextField(blank=True, verbose_name="Descripción")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Registro de Horas"
        verbose_name_plural = "Registros de Horas"

    def __str__(self):
        return f"{self.analyst} — {self.hours}h — {self.date}"
