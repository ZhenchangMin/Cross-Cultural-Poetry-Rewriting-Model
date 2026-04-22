package com.example.demo.model;

public class Poem {
    private String text;
    private String style;
    private String targetCulture;
    private String emotion;

    public String getText() { return text; }
    public void setText(String text) { this.text = text; }

    public String getStyle() { return style; }
    public void setStyle(String style) { this.style = style; }

    public String getTargetCulture() { return targetCulture; }
    public void setTargetCulture(String targetCulture) { this.targetCulture = targetCulture; }

    public String getEmotion() { return emotion; }
    public void setEmotion(String emotion) { this.emotion = emotion; }
}
