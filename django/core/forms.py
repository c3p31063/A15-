# django/core/forms.py
# -*- coding: utf-8 -*-
"""
core.forms（完全版）

Django 側で利用可能なフォーム定義。

現状の views では Django 標準の AuthenticationForm / UserCreationForm を
直接使っているため必須ではないが、

- 画像チェックフォーム
- テキストチェックフォーム

をここで定義しておくことで、将来的にバリデーションやラベルを整理しやすくする。
"""

from __future__ import annotations

from typing import Any

from django import forms


class ImageCheckForm(forms.Form):
    """
    画像チェック用フォーム。

    - 画像ファイル (必須)
    - プロンプト / 補足説明 (任意)
    """

    image = forms.ImageField(
        label="チェック対象画像",
        required=True,
        help_text="著作権リスクをチェックしたい画像ファイルを選択してください。",
    )
    prompt = forms.CharField(
        label="生成時のプロンプト / 補足説明（任意）",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "画像生成AIを使った場合、そのときのプロンプトなどを記入してください（任意）。",
            }
        ),
    )

    def clean_image(self) -> Any:
        """
        画像の簡易バリデーション（サイズや拡張子などをチェックしたければここで）。
        """
        img = self.cleaned_data.get("image")
        if img is None:
            return img

        # 例: 10MB 超えを禁止（必要なければコメントアウト）
        max_size_mb = 10
        if img.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(f"画像サイズは {max_size_mb} MB 以下にしてください。")

        return img


class TextCheckForm(forms.Form):
    """
    テキストチェック用フォーム。

    - チェック対象テキスト（必須）
    """

    text = forms.CharField(
        label="チェック対象テキスト",
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "著作権リスクをチェックしたいテキストを貼り付けてください。",
            }
        ),
    )

    def clean_text(self) -> str:
        """
        テキストの簡易バリデーション。
        """
        value = self.cleaned_data.get("text", "")
        if not value.strip():
            raise forms.ValidationError("チェック対象のテキストを入力してください。")

        # 例: 極端に長すぎる場合に警告（FastAPI 側でもトリムしているが、フロント側でも軽く制限）
        max_len = 20000
        if len(value) > max_len:
            raise forms.ValidationError(f"テキストが長すぎます（最大 {max_len} 文字まで）。")

        return value
