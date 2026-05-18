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
                你是一位精通中、俄、韩三国诗学，并深谙韦努蒂（Lawrence Venuti, 1995）翻译理论的文学转写专家。
                你的任务不是翻译（translation），而是基于「异化（foreignization）/ 归化（domestication）」框架进行「诗歌跨文化转写（poetry transcreation）」。

                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                【原诗】
                语言：%s
                内容：
                %s

                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                【目标形式（硬性约束，必须遵守）】
                目标语言与体裁：%s
                形式规范：%s

                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                【文化适配强度 = %d / 5】
                此参数刻度对应韦努蒂提出的两种翻译策略，刻度越小越「异化」，越大越「归化」。
                请严格按当前刻度，在 ①意象 ②典故/文化负载词 ③句法节奏 ④修辞色彩 ⑤读者体验 五个维度上**一致地**体现该立场——
                绝不可只调整意象层，而其他维度自行妥协。

                两极完整内涵（供你校准）：

                ◆ 1 端：极端异化 Foreignization
                  - 立场：以源语文化为中心，最大限度保留源诗的"他者性 / 陌生感"
                  - 意象：完整保留源语特有意象（俄语：白桦、伏特加、草原、教堂金顶；韩语：无穷花、汉江、螺钿、판소리）
                  - 典故：保留原典故、人名、地名，不做本土化替换
                  - 句法节奏：允许保留源语典型语序与"翻译腔"，可有意识地异质化
                  - 修辞：保留源语美学（俄诗的崇高与沉郁；韩诗的"恨"与情）
                  - 读者体验：让读者明确感到"这是一首外国诗"，可生硬，但绝不熨平
                  - 形式：仍按【目标形式】写（这是硬约束），但内容、意象、修辞坚守源语本色

                ◆ 5 端：极端归化 Domestication
                  - 立场：以目标语读者为中心，让作品读起来像目标文化本土原创
                  - 意象：源语意象全部置换为目标文化对应物（俄白桦→中翠竹/孤松；韩无穷花→中梅）
                  - 典故：使用目标文化典故、地名、历史人物
                  - 句法节奏：完全符合目标语诗学习惯，消除一切"翻译腔"
                  - 修辞：纯粹的目标文化美学（中文的含蓄留白；俄诗的庄严铺陈；韩诗的悠长哀婉）
                  - 读者体验：让读者感觉"这是一首本国诗"，外国痕迹尽量消除

                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                【当前刻度的具体处理要求】
                %s

                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                【不可越过的底线（适用于任何强度）】
                1. 情感内核 / 精神主题必须与原诗一致——这是转写的底线
                2. 必须严格遵守【目标形式】的字数、行数、押韵等硬性约束
                3. 不得编造原诗没有的事件、人物或叙事

                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                【输出格式】（严格遵守，不要添加任何额外说明）

                【转写结果】
                （在此输出转写后的诗，符合【目标形式】约束）

                【转写思路】
                - 异化/归化策略（强度 %d/5）：（一句话说明你如何在五个维度上体现该刻度立场）
                - 关键意象处理：（说明哪些源语意象被保留 / 并置 / 替换，以及替换为什么）
                - 句法与修辞色彩：（一句话说明节奏与修辞向源语还是目标语贴近）
                - 保留的精神内核：（一句话说明原诗的情感核心如何在转写中延续）
                """,
                sourceName,
                poem.getText(),
                targetName + styleName,
                outputForm,
                intensity,
                intensitySpec(intensity, sourceName, targetName),
                intensity
        );
    }

    /**
     * 根据当前强度生成该刻度的具体处理指令，避免模型把强度退化为只调意象比例。
     */
    private String intensitySpec(int intensity, String sourceName, String targetName) {
        return switch (intensity) {
            case 1 -> String.format("""
                    立场：极端异化。读者读完应明确感到"这是一首%s诗"。
                    - 意象：%s特有意象**完整保留**，不替换、不并置（如俄语保留"白桦/草原/伏特加"，韩语保留"无穷花/汉江/판소리"）。
                    - 典故/人名/地名：**全部保留原貌**，必要时音译以保留外来感。
                    - 句法节奏：保留源语典型语序，可有意识地保留"翻译腔"。
                    - 修辞色彩：完全使用%s诗学的修辞习惯。
                    - 读者体验：可生硬、可陌生，但绝不本土化、绝不熨平。""",
                    sourceName, sourceName, sourceName);
            case 2 -> String.format("""
                    立场：偏异化。
                    - 意象：%s意象为主体并保留；仅对目标读者**完全无法理解**的极少数元素加最低限度的解释性补足，但不替换。
                    - 典故/人名/地名：保留为主。
                    - 句法节奏：保留源语"陌生感"，节奏不刻意贴合目标语习惯。
                    - 修辞色彩：以源语美学为主，少量目标语修辞协助理解。
                    - 读者体验：读者仍能明确感到"这是异国之作"。""", sourceName);
            case 3 -> String.format("""
                    立场：折中并置。
                    - 意象：%s意象与%s意象**并置**或互文（如"白桦"与"梅"同框、"汉江"与"长江"互文），让两种文化在同一首诗中对话。
                    - 典故：源语典故与目标语典故各占其位。
                    - 句法节奏：源语陌生感与目标语熟悉感各半。
                    - 修辞色彩：两种诗学美学兼有。
                    - 读者体验：读者能同时感受到"异国"与"熟悉"两层。""",
                    sourceName, targetName);
            case 4 -> String.format("""
                    立场：偏归化。
                    - 意象：**主要使用%s意象与典故**；仅保留 1–2 个源诗最具标志性的元素作为"异质遗痕"提醒读者其外国出身。
                    - 句法节奏：基本贴近%s诗学习惯。
                    - 修辞色彩：向%s美学贴近。
                    - 读者体验：读起来已接近本国诗，但仍有可识别的外国痕迹。""",
                    targetName, targetName, targetName);
            case 5 -> String.format("""
                    立场：极端归化。读者读完应感觉"这就是一首%s诗"，外国痕迹消除殆尽。
                    - 意象：%s源语意象**全部置换**为%s文化对应物（俄"白桦"→中"翠竹/孤松"；韩"无穷花"→中"梅"；中"梅兰竹菊"→俄"白桦/橡树/雪原"等）。
                    - 典故/人名/地名：**全部替换**为%s文化典故、地名、历史人物。
                    - 句法节奏：完全符合%s诗学习惯，消除一切"翻译腔"。
                    - 修辞色彩：纯%s诗学美学。
                    - 读者体验：让读者感觉"这是一首本国原创诗"。""",
                    targetName, sourceName, targetName, targetName, targetName, targetName);
            default -> intensitySpec(3, sourceName, targetName);
        };
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
                        "你是基于韦努蒂（Venuti, 1995）异化/归化理论框架的跨文化诗歌转写专家。" +
                        "对任何给定的【文化适配强度】，你必须在意象、典故、句法节奏、修辞色彩、读者体验五个维度上一致地体现该立场，" +
                        "而不是只调整意象比例。严格按要求的【输出格式】输出，不要添加任何额外说明。"),
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
