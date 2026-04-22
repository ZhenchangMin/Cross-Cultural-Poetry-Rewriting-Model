package com.example.demo.repository;

import com.example.demo.model.Poem;
import java.util.List;

public interface PoemRepository {
    void save(Poem poem);
    List<Poem> findAll();
}
