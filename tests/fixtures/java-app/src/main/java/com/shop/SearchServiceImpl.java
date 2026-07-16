package com.shop;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import org.springframework.cache.annotation.Cacheable;

@Service
public class SearchServiceImpl implements SearchService {
    private final ProductRepository productRepository;
    private final PricingClient pricingClient;
    private final RestTemplate restTemplate;

    public SearchServiceImpl(ProductRepository productRepository, PricingClient pricingClient, RestTemplate restTemplate) {
        this.productRepository = productRepository;
        this.pricingClient = pricingClient;
        this.restTemplate = restTemplate;
    }

    @Override
    @Transactional(readOnly = true)
    @Cacheable("search")
    public SearchResult search(String query) {
        return new SearchResult(productRepository.findByNameContaining(query));
    }
}
