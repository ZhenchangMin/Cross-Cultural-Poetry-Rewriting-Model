package com.example.demo.controller;

import com.example.demo.model.Poem;
import com.example.demo.service.PoemService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/translate")
@CrossOrigin(origins = {"http://localhost:8080", "http://localhost:8081", "http://localhost:8082"})
public class PoemController {

    @Autowired
    private PoemService poemService;

    @PostMapping
    public Map<String, String> translate(@RequestBody Poem poem) {
        return poemService.generatePoem(poem);
    }
}
