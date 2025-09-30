from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class CheckJob(models.Model):
    KIND_CHOICES = [("image","image"),("text","text")]
    STATUS = [("pending","pending"),("running","running"),("done","done"),("rejected","rejected")]
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    kind = models.CharField(max_length=8, choices=KIND_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    prompt_text = models.TextField(blank=True)
    tool_name = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

class CheckResult(models.Model):
    job = models.OneToOneField(CheckJob, on_delete=models.CASCADE, related_name="result")
    risk_score_total = models.FloatField()
    risk_level = models.CharField(max_length=12)
    decision = models.CharField(max_length=16)
    threshold_version = models.CharField(max_length=32)

class Evidence(models.Model):
    job = models.ForeignKey(CheckJob, on_delete=models.CASCADE, related_name="evidences")
    source = models.CharField(max_length=32)
    raw_json = models.JSONField(default=dict)
    score_numeric = models.FloatField()
    label = models.CharField(max_length=64, blank=True)
    url = models.TextField(blank=True)

class SimilarImage(models.Model):
    job = models.ForeignKey(CheckJob, on_delete=models.CASCADE, related_name="similar_images")
    rank = models.IntegerField()
    match_url = models.TextField()
    match_score = models.FloatField()
    thumbnail_url = models.TextField(blank=True)

class PolicySnapshot(models.Model):
    version = models.CharField(max_length=32, unique=True)
    weights_json = models.JSONField(default=dict)
    thresholds_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.version
