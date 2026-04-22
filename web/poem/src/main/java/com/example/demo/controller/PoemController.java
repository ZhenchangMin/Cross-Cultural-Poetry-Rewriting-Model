package com.example.poemproject.controller;

import com.example.poemproject.service.PoemService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/translate")
public class PoemController {

    @Autowired
    private PoemService poemService;

    @PostMapping
    public String translate(@RequestBody String poem) {
        return poemService.translatePoem(poem);
    }
}