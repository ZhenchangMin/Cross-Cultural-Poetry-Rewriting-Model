package com.example.demo.model;

public class Poem {
    private String text;
    private String style;
    private String sourceLang;
    private String targetLang;
    private String emotion;

    public String getText() { return text; }
    public void setText(String text) { this.text = text; }

    public String getStyle() { return style; }
    public void setStyle(String style) { this.style = style; }

    public String getSourceLang() { return sourceLang; }
    public void setSourceLang(String sourceLang) { this.sourceLang = sourceLang; }

    public String getTargetLang() { return targetLang; }
    public void setTargetLang(String targetLang) { this.targetLang = targetLang; }

    public String getEmotion() { return emotion; }
    public void setEmotion(String emotion) { this.emotion = emotion; }
}
