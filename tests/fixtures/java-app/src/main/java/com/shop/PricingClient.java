package com.shop;
import org.springframework.cloud.openfeign.FeignClient;
@FeignClient(name = "pricing")
public interface PricingClient {
    double priceFor(Long productId);
}
