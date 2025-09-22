from django.contrib import admin
from .models import CheckJob, CheckResult, Evidence, SimilarImage, PolicySnapshot

@admin.register(CheckJob)
class CheckJobAdmin(admin.ModelAdmin):
    list_display = ("id","kind","status","created_at","finished_at")
    list_filter = ("kind","status")

@admin.register(CheckResult)
class CheckResultAdmin(admin.ModelAdmin):
    list_display = ("job","risk_score_total","risk_level","decision","threshold_version")

@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("job","source","score_numeric","label","url")

@admin.register(SimilarImage)
class SimilarImageAdmin(admin.ModelAdmin):
    list_display = ("job","rank","match_score","match_url")

@admin.register(PolicySnapshot)
class PolicySnapshotAdmin(admin.ModelAdmin):
    list_display = ("version","created_at")
