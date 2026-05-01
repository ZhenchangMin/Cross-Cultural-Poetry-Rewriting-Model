package com.example.demo.model;

public class Poem {
    private String text;
    private String style;
    private String sourceLang;
    private String targetLang;
    private Integer intensity;  // 1=异化 … 5=归化，null 时默认 3

    public String getText() { return text; }
    public void setText(String text) { this.text = text; }

    public String getStyle() { return style; }
    public void setStyle(String style) { this.style = style; }

    public String getSourceLang() { return sourceLang; }
    public void setSourceLang(String sourceLang) { this.sourceLang = sourceLang; }

    public String getTargetLang() { return targetLang; }
    public void setTargetLang(String targetLang) { this.targetLang = targetLang; }

    public Integer getIntensity() { return intensity; }
    public void setIntensity(Integer intensity) { this.intensity = intensity; }
}
