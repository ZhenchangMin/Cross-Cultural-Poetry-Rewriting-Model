package com.example.demo.service;

import com.example.demo.model.Poem;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class PoemService {

    public Map<String, String> generatePoem(Poem poem) {
        // TODO: 接入 AI 模型替换此占位实现
        String result = String.format("【%s-%s-%s风格】\n%s\n（AI改写示例）",
                poem.getTargetCulture(), poem.getStyle(), poem.getEmotion(), poem.getText());
        return Map.of("result", result);
    }
}
