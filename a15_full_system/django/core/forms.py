from django import forms

class UploadForm(forms.Form):
    KIND_CHOICES = [("image","画像"),("text","テキスト")]
    kind = forms.ChoiceField(choices=KIND_CHOICES)
    prompt = forms.CharField(required=False)
    image = forms.ImageField(required=False)
    text = forms.CharField(widget=forms.Textarea, required=False)

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        if kind == "image" and not cleaned.get("image"):
            raise forms.ValidationError("画像を選択してください")
        if kind == "text" and not cleaned.get("text"):
            raise forms.ValidationError("テキストを入力してください")
        return cleaned
