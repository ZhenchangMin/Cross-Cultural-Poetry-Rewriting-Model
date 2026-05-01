package com.example.demo.service;

import com.example.demo.model.Poem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class PoemService {

    private static final Logger log = LoggerFactory.getLogger(PoemService.class);
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
            log.error("DEEPSEEK_API_KEY not set");
            return Map.of("result", "错误：未配置 DEEPSEEK_API_KEY 环境变量");
        }
        try {
            String prompt = buildPrompt(poem);
            log.info("Sending prompt (first 100 chars): {}", prompt.substring(0, Math.min(100, prompt.length())));
            String result = callDeepSeek(apiKey, prompt);
            log.info("Received response (first 100 chars): {}", result.substring(0, Math.min(100, result.length())));
            return Map.of("result", result);
        } catch (HttpClientErrorException e) {
            log.error("DeepSeek client error: {} {}", e.getStatusCode(), e.getResponseBodyAsString());
            return Map.of("result", "API 请求错误 " + e.getStatusCode() + "：" + e.getResponseBodyAsString());
        } catch (HttpServerErrorException e) {
            log.error("DeepSeek server error: {} {}", e.getStatusCode(), e.getResponseBodyAsString());
            return Map.of("result", "API 服务器错误 " + e.getStatusCode() + "，请稍后重试");
        } catch (Exception e) {
            log.error("Unexpected error calling DeepSeek", e);
            return Map.of("result", "生成失败：" + e.getMessage());
        }
    }

    private String buildPrompt(Poem poem) {
        String sourceName  = langDisplayName(poem.getSourceLang());
        String targetName  = langDisplayName(poem.getTargetLang());
        String styleName   = "classical".equals(poem.getStyle()) ? "古典" : "现代";
        int    intensity   = poem.getIntensity() != null ? poem.getIntensity() : 3;
        String outputForm  = outputFormName(poem.getTargetLang(), styleName);

        return String.format("""
                你是一位精通中、俄、韩三国诗学的文学转写专家。
                你的任务不是翻译（translation），而是"诗歌跨文化转写（poetry transcreation）"。

                【转写 vs 翻译的区别】
                - 翻译：以原文为主，目标语言服务于原文
                - 转写：以原诗为灵感种子，在目标文化的诗学体系中重新创作一首"对应的诗"
                - 让懂目标语言诗歌的读者读到时，能感受到与原作相通的精神核心

                【原诗】
                语言：%s
                内容：
                %s

                【转写参数】
                目标诗学风格：%s
                形式约束：%s
                文化适配强度：%d/5
                （1=尽量保留原文化的异质性、陌生感；5=完全归化为目标文化诗歌，外国痕迹尽量消除）
                重点保留维度：意象、情感内核、格律美感

                【转写原则】
                1. 意象转换：核心意象保留其象征功能，可视强度置换为目标文化中的对应物
                   - 强度 1-2：保留原意象（如"白桦"、"红豆"）
                   - 强度 3：原意象与目标文化意象并置
                   - 强度 4-5：替换为目标文化意象（如中文中的"梅"或"竹"）
                2. 形式重构：按形式约束重组，不必行行对应
                3. 文化负载词：视强度决定保留或替换为目标文化对应语汇
                4. 情感内核：必须保留——这是转写不可越过的底线

                【输出格式】
                请严格按以下格式输出，不要添加额外说明：

                【转写结果】
                （在此输出转写后的诗，符合形式约束）

                【转写思路】
                - 意象处理：（一句话说明）
                - 形式选择：（一句话说明）
                - 文化适配：（一句话说明）
                - 保留的精神内核：（一句话说明）
                """,
                sourceName,
                poem.getText(),
                targetName + styleName + "诗",
                outputForm,
                intensity
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

    private String outputFormName(String targetLang, String styleName) {
        if (targetLang == null) targetLang = "ZH";
        return switch (targetLang) {
            case "KO" -> styleName + "韩语时调（시조）：共三行，每行分前后句，音节约 3-4-4-4 / 3-4-4-4 / 3-5-4-3";
            case "RU" -> styleName + "俄语格律诗：共八行，押韵方案 ABABCDCD，保持俄语诗意与韵律感";
            default   -> styleName + "中文七律：共八句，每句七字，偶数句末字押韵（二、四、六、八句）";
        };
    }

    @SuppressWarnings("unchecked")
    private String callDeepSeek(String apiKey, String prompt) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(apiKey);

        Map<String, Object> body = new HashMap<>();
        body.put("model", "deepseek-chat");
        body.put("messages", List.of(
                Map.of("role", "system", "content",
                        "你是跨文化诗歌转写专家。严格按要求的【输出格式】输出，不加任何额外说明。"),
                Map.of("role", "user", "content", prompt)
        ));
        body.put("temperature", 0.8);
        body.put("max_tokens", 1200);

        ResponseEntity<Map> resp = restTemplate.postForEntity(
                DEEPSEEK_URL, new HttpEntity<>(body, headers), Map.class);

        List<Map<String, Object>> choices =
                (List<Map<String, Object>>) resp.getBody().get("choices");
        Map<String, Object> message =
                (Map<String, Object>) choices.get(0).get("message");
        return ((String) message.get("content")).trim();
    }
}
