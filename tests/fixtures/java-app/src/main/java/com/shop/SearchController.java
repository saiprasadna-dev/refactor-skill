package com.shop;
import org.springframework.web.bind.annotation.*;
import javax.validation.Valid;

@RestController
@RequestMapping("/api")
public class SearchController {
    private final SearchService searchService;
    public SearchController(SearchService searchService) { this.searchService = searchService; }

    @GetMapping("/search")
    @PreAuthorize("hasRole('USER')")
    public SearchResult search(@RequestParam @Valid String query) {
        return searchService.search(query);
    }
}
