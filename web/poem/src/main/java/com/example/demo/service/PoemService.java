package com.example.poemproject.service;

import org.springframework.stereotype.Service;

@Service
public class PoemService {

    public String translatePoem(String poem) {
        // 这里可以用AI模型来生成翻译的诗歌
        return "这是翻译后的诗歌：" + poem;
    }
}