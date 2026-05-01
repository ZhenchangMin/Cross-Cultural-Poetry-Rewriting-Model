package com.example.demo.service;

import com.example.demo.model.Poem;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class PoemService {

    private static final String DEEPSEEK_URL = "https://api.deepseek.com/chat/completions";

    private final RestTemplate restTemplate;

    public PoemService() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);
        factory.setReadTimeout(60_000);
        this.restTemplate = new RestTemplate(factory);
    }

    public Map<String, String> generatePoem(Poem poem) {
        String apiKey = System.getenv("DEEPSEEK_API_KEY");
        if (apiKey == null || apiKey.isBlank()) {
            return Map.of("result", "错误：未配置 DEEPSEEK_API_KEY 环境变量");
        }
        try {
            String result = callDeepSeek(apiKey, buildPrompt(poem));
            return Map.of("result", result);
        } catch (Exception e) {
            return Map.of("result", "生成失败：" + e.getMessage());
        }
    }

    private String buildPrompt(Poem poem) {
        String sourceName = langDisplayName(poem.getSourceLang());
        String targetName = langDisplayName(poem.getTargetLang());
        String styleName  = "classical".equals(poem.getStyle()) ? "古典" : "现代";
        String emotion = poem.getEmotion() != null ? poem.getEmotion() : "neutral";
        String emotionName = switch (emotion) {
            case "melancholy" -> "忧郁感伤";
            case "joyful"     -> "欢快明朗";
            default           -> "平和中正";
        };
        String outputFormat = outputFormatInstruction(poem.getTargetLang(), styleName);

        return String.format("""
                你是一位精通跨文化诗歌创作的诗人，能将不同语言的诗歌改写为目标语言的经典诗体。

                源诗语言：%s
                目标语言：%s
                情感基调：%s

                原诗：
                %s

                请将上述诗歌的核心意象、情感和主题，按照以下要求改写：
                %s
                情感基调保持「%s」。
                只输出诗歌正文，不要标题、序号和任何解释。
                """,
                sourceName, targetName, emotionName,
                poem.getText(),
                outputFormat, emotionName
        );
    }

    private String langDisplayName(String lang) {
        if (lang == null) return "中文";
        return switch (lang) {
            case "KO" -> "韩语";
            case "RU" -> "俄语";
            default   -> "中文";
        };
    }

    private String outputFormatInstruction(String targetLang, String styleName) {
        if (targetLang == null) targetLang = "ZH";
        return switch (targetLang) {
            case "KO" -> """
                    改写为韩国传统时调（시조）格式：
                    - 共三行（初章、中章、终章）
                    - 每行由两个半句构成，音节数约为 3-4-4-4 / 3-4-4-4 / 3-5-4-3
                    - 使用%s风格的韩语表达""".formatted(styleName);
            case "RU" -> """
                    改写为俄语格律诗：
                    - 共八行，押韵方案 ABABCDCD
                    - 使用%s风格的俄语表达，保持诗意与韵律感""".formatted(styleName);
            default   -> """
                    改写为中国传统七律：
                    - 共八句，每句七字
                    - 偶数句末字押韵（二、四、六、八句）
                    - 使用%s风格的汉语表达""".formatted(styleName);
        };
    }

    @SuppressWarnings("unchecked")
    private String callDeepSeek(String apiKey, String prompt) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(apiKey);

        Map<String, Object> body = new HashMap<>();
        body.put("model", "deepseek-chat");
        body.put("messages", List.of(Map.of("role", "user", "content", prompt)));
        body.put("temperature", 0.8);
        body.put("max_tokens", 400);

        ResponseEntity<Map> resp = restTemplate.postForEntity(
                DEEPSEEK_URL, new HttpEntity<>(body, headers), Map.class);

        List<Map<String, Object>> choices =
                (List<Map<String, Object>>) resp.getBody().get("choices");
        Map<String, Object> message =
                (Map<String, Object>) choices.get(0).get("message");
        return ((String) message.get("content")).trim();
    }
}
