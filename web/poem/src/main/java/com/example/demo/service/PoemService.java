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
        String styleName   = styleDisplayName(poem.getStyle());
        int    intensity   = poem.getIntensity() != null ? poem.getIntensity() : 3;
        String outputForm  = outputFormName(poem.getTargetLang(), poem.getStyle());

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
                targetName + styleName,
                outputForm,
                intensity
        );
    }

    private String styleDisplayName(String styleCode) {
        if (styleCode == null) return "现代诗";
        return switch (styleCode) {
            case "jueju"  -> "绝句";
            case "lvshi"  -> "律诗";
            case "ci"     -> "宋词";
            case "qu"     -> "元曲";
            case "sijo"   -> "时调";
            case "gasa"   -> "歌辞";
            case "sonnet" -> "十四行诗";
            case "ode"    -> "颂诗";
            case "lyric"  -> "抒情诗";
            case "modern" -> "现代诗";
            // 兼容旧值
            case "classical" -> "古典诗";
            default       -> "现代诗";
        };
    }

    private String langDisplayName(String lang) {
        if (lang == null) return "中文";
        return switch (lang) {
            case "KO" -> "韩语";
            case "RU" -> "俄语";
            default   -> "中文";
        };
    }

    private String outputFormName(String targetLang, String styleCode) {
        String code = styleCode == null ? "modern" : styleCode;
        return switch (code) {
            // 中文古典诗体
            case "jueju" -> "中文绝句：四句，每句七字（或可写五言绝句五字），第二、四句末字押平声韵";
            case "lvshi" -> "中文律诗（七律）：共八句，每句七字，第二、四、六、八句末字押平声韵；颔联（三四句）与颈联（五六句）须对仗";
            case "ci"    -> "宋词：依词牌长短句结构创作（推荐如《如梦令》《浣溪沙》《虞美人》《水调歌头》等），请在【转写结果】首行标注词牌名";
            case "qu"    -> "元曲（散曲小令）：以小令形式创作（推荐如《天净沙》《山坡羊》《沉醉东风》等），请在【转写结果】首行标注曲牌名，可加衬字，语言可较直白";
            // 韩语古典诗体
            case "sijo"  -> "韩语时调（시조）：三行结构，每行分前后句，音节约 3-4-4-4 / 3-4-4-4 / 3-5-4-3，第三行首句须含转折（종장의 첫 음보）";
            case "gasa"  -> "韩语歌辞（가사）：四音步长行体，行数不固定，节奏自由，叙抒结合，使用古典韩语诗体风格";
            // 俄语诗体
            case "sonnet" -> "俄语十四行诗：14 行，押韵方案 ABAB CDCD EFEF GG（莎士比亚式）或 ABBA ABBA CDC DCD（彼特拉克式），任择其一";
            case "ode"    -> "俄语颂诗：庄严抒情风格，由多个四行节构成，每节押 ABAB 或 AABB，语言典雅";
            case "lyric"  -> "俄语抒情格律诗：共 8 行，押韵方案 ABABCDCD，重视音步与情感张力";
            // 现代自由体
            case "modern" -> modernForm(targetLang);
            // 兼容旧值
            case "classical" -> defaultClassicalForm(targetLang);
            default -> modernForm(targetLang);
        };
    }

    private String modernForm(String targetLang) {
        if (targetLang == null) targetLang = "ZH";
        return switch (targetLang) {
            case "KO" -> "韩语现代诗：自由体，无固定格律，注重意象凝练与节奏感";
            case "RU" -> "俄语现代诗（自由体）：不严格押韵，重视意象与语感张力";
            default   -> "中文现代诗：自由体，无格律约束，注重意象与节奏";
        };
    }

    private String defaultClassicalForm(String targetLang) {
        if (targetLang == null) targetLang = "ZH";
        return switch (targetLang) {
            case "KO" -> "韩语时调（시조）：三行结构，音节约 3-4-4-4 / 3-4-4-4 / 3-5-4-3";
            case "RU" -> "俄语格律诗：8 行，押韵 ABABCDCD";
            default   -> "中文七律：八句七言，偶数句末押平声韵";
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
