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
                【不可越过的底线（按优先级排列；任何强度下均适用，凌驾于异化/归化策略之上）】
                1. **专有名词忠实**：原诗中所有**人名、地名、朝代/王朝名、特定历史事件名、特定文化机构名**必须忠实保留，按目标语习惯音译。
                   - 不得意译（如"Пушкин"不可译为"诗人"）；
                   - 不得替换为目标文化的对应人物或地点（如"莫斯科"不可改为"长安"，"普希金"不可改为"李白"）；
                   - 此规则即使在强度=5（极端归化）下也不可松动。
                2. **形式严格合规**：必须满足【目标形式】中列出的**所有**硬性指标（字数、行数、押韵方案、对仗位置等）——形式是本项目的核心，缺一项即视为不合格。
                3. 情感内核 / 精神主题必须与原诗一致。
                4. 不得编造原诗没有的事件、人物或叙事。

                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                【输出前的内部自检（必须执行，不要写入输出）】
                输出前，请在内部逐项核对以下硬指标；任一项不合规，请转写直到全部合规再输出：
                A. 形式自检：对照【目标形式】——字数对吗？行数对吗？押韵符合规定方案吗？需对仗的位置对仗了吗？词牌/曲牌名标注了吗？
                B. 专有名词自检：原诗中所有人名/地名/特定文化符号是否在转写中全部出现（以音译形式）？是否有被意译或替换？

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
        // 注意：专有名词（人名/地名）的处理由【底线1】统一规定（任何强度下均须忠实保留+音译），
        // 此处的强度调节仅适用于**非专名性的文化负载词**（如意象、典故、修辞、句法）。
        return switch (intensity) {
            case 1 -> String.format("""
                    立场：极端异化。读者读完应明确感到"这是一首%s诗"。
                    - 文化意象：%s特有意象（非专名类，如俄语"白桦/草原/伏特加"，韩语"无穷花/판소리"）**完整保留**，不替换、不并置。
                    - 非专名性典故/文化负载词：保留原貌，必要时音译。
                    - 句法节奏：保留源语典型语序，可有意识地保留"翻译腔"。
                    - 修辞色彩：完全使用%s诗学的修辞习惯。
                    - 读者体验：可生硬、可陌生，但绝不本土化、绝不熨平。""",
                    sourceName, sourceName, sourceName);
            case 2 -> String.format("""
                    立场：偏异化。
                    - 文化意象：%s意象为主体并保留；仅对目标读者**完全无法理解**的极少数元素加最低限度的解释性补足，但不替换。
                    - 非专名性典故/文化负载词：保留为主。
                    - 句法节奏：保留源语"陌生感"，节奏不刻意贴合目标语习惯。
                    - 修辞色彩：以源语美学为主，少量目标语修辞协助理解。
                    - 读者体验：读者仍能明确感到"这是异国之作"。""", sourceName);
            case 3 -> String.format("""
                    立场：折中并置。
                    - 文化意象：%s意象与%s意象**并置**或互文（如"白桦"与"梅"同框、"汉江"与"长江"互文），让两种文化在同一首诗中对话。
                    - 非专名性典故：源语典故与目标语典故各占其位。
                    - 句法节奏：源语陌生感与目标语熟悉感各半。
                    - 修辞色彩：两种诗学美学兼有。
                    - 读者体验：读者能同时感受到"异国"与"熟悉"两层。""",
                    sourceName, targetName);
            case 4 -> String.format("""
                    立场：偏归化。
                    - 文化意象：**主要使用%s意象**；仅保留 1–2 个源诗最具标志性的非专名意象作为"异质遗痕"提醒读者其外国出身。
                    - 非专名性典故/文化负载词：主要使用%s文化对应物。
                    - 句法节奏：基本贴近%s诗学习惯。
                    - 修辞色彩：向%s美学贴近。
                    - 读者体验：读起来已接近本国诗，但仍有可识别的外国痕迹（包括底线保留的专有名词音译）。""",
                    targetName, targetName, targetName, targetName);
            case 5 -> String.format("""
                    立场：极端归化。读者读完应感觉"这首诗的修辞与意象都很%s"，但**专有名词仍须按底线1保留音译**（这是不可突破的底线，不是异质遗痕的让步）。
                    - 文化意象：%s源语意象（非专名类）**全部置换**为%s文化对应物（俄"白桦"→中"翠竹/孤松"；韩"无穷花"→中"梅"；中"梅兰竹菊"→俄"白桦/橡树/雪原"等）。
                    - 非专名性典故/文化负载词：**全部替换**为%s文化对应物。
                    - 句法节奏：完全符合%s诗学习惯，消除一切"翻译腔"。
                    - 修辞色彩：纯%s诗学美学。
                    - 读者体验：除了保留的专有名词音译外，让读者感觉行文与意象本土化。""",
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
            case "jueju" -> """
                    中文绝句：硬性指标——
                      [行数] 共 4 句；
                      [字数] 七绝每句 7 字（全诗 28 字），或五绝每句 5 字（全诗 20 字），二者择一；
                      [押韵] 第 2、4 句末字押同一平声韵；
                      [一致性] 全诗字数整齐，不可参差。""";
            case "lvshi" -> """
                    中文律诗（七律）：硬性指标——
                      [行数] 共 8 句；
                      [字数] 每句 7 字，全诗 56 字；
                      [押韵] 第 2、4、6、8 句末字押同一平声韵；
                      [对仗] 颔联（第 3-4 句）与颈联（第 5-6 句）须工对：词性相对、平仄相对；
                      [一致性] 全诗字数整齐，不可参差。""";
            case "ci"    -> """
                    宋词：硬性指标——
                      [词牌] 请在【转写结果】首行单独标注词牌名（如《如梦令》），格式："《词牌名》"；
                      [结构] 严格按所选词牌规定的句数、各句字数、韵脚位置创作，不得自创句式；
                      [推荐词牌] 《如梦令》《浣溪沙》《虞美人》《水调歌头》。""";
            case "qu"    -> """
                    元曲（散曲小令）：硬性指标——
                      [曲牌] 请在【转写结果】首行单独标注曲牌名（如《天净沙》），格式："《曲牌名》"；
                      [结构] 严格按所选曲牌的句数、字数、韵脚创作；
                      [语言] 可加衬字，语言可较直白；
                      [推荐曲牌] 《天净沙》《山坡羊》《沉醉东风》。""";
            // 韩语古典诗体
            case "sijo"  -> """
                    韩语时调（시조）：硬性指标——
                      [行数] 共 3 行（초장、중장、종장），每行分前句与后句；
                      [音节] 音节结构 3-4-3-4 / 3-4-3-4 / 3-5-4-3，允许 ±1 弹性；
                      [转折] 第 3 行（종장）的第一音步**必须固定为 3 音节**，并含语义转折。""";
            case "gasa"  -> """
                    韩语歌辞（가사）：硬性指标——
                      [节奏] 四音步长行体（每行 3-4-3-4 或 4-4-4-4 音节）；
                      [行数] 偶数行，建议 8-16 行；
                      [风格] 叙抒结合，使用古典韩语诗体风格。""";
            // 俄语诗体
            case "sonnet" -> """
                    俄语十四行诗：硬性指标——
                      [行数] 严格 14 行；
                      [押韵] 押韵方案二选一：莎士比亚式 ABAB CDCD EFEF GG，或彼特拉克式 ABBA ABBA CDC DCD；
                      [音步] 推荐五步抑扬格（ямб），每行音步整齐。""";
            case "ode"    -> """
                    俄语颂诗：硬性指标——
                      [结构] 由 ≥3 个四行节（quatrain）构成；
                      [押韵] 每节押 ABAB 或 AABB；
                      [风格] 庄严抒情，语言典雅。""";
            case "lyric"  -> """
                    俄语抒情格律诗：硬性指标——
                      [行数] 共 8 行；
                      [押韵] 押韵方案 ABABCDCD；
                      [节奏] 音步整齐，重视情感张力。""";
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
            case "KO" -> """
                    韩语现代诗：硬性指标——
                      [体式] 分行自由体，无固定格律；
                      [行数] 建议 6-20 行；
                      [要求] 注重意象凝练与节奏感，需有清晰的意象单元与断句。""";
            case "RU" -> """
                    俄语现代诗（自由体）：硬性指标——
                      [体式] 分行自由体，不严格押韵；
                      [行数] 建议 6-20 行；
                      [要求] 重视意象与语感张力，需有清晰的意象单元与断句。""";
            default   -> """
                    中文现代诗：硬性指标——
                      [体式] 分行自由体，无格律约束；
                      [行数] 建议 6-20 行；
                      [要求] 注重意象与节奏，需有清晰的意象单元与断句。""";
        };
    }

    private String defaultClassicalForm(String targetLang) {
        if (targetLang == null) targetLang = "ZH";
        return switch (targetLang) {
            case "KO" -> "韩语时调（시조）：3 行结构，音节 3-4-3-4 / 3-4-3-4 / 3-5-4-3，종장首音步固定 3 音节并含转折";
            case "RU" -> "俄语格律诗：8 行，押韵 ABABCDCD";
            default   -> "中文七律：8 句 7 言，2/4/6/8 句末押平声韵，颔联颈联须对仗";
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
                        "你必须遵守两条不可妥协的底线：" +
                        "(1) 原诗中的**专有名词**（人名、地名、朝代名、特定历史事件名、特定文化机构名）须忠实保留，按目标语习惯音译，绝不可意译、绝不可替换为目标文化的对应人物或地点；" +
                        "(2) 必须严格满足用户选定目标诗体的所有硬性形式指标（字数、行数、押韵、对仗等）。" +
                        "在这两条底线之上，你才在【文化适配强度】指引下，于意象、典故、句法节奏、修辞色彩、读者体验五个维度上一致地体现该立场。" +
                        "严格按要求的【输出格式】输出，不要添加任何额外说明。"),
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
