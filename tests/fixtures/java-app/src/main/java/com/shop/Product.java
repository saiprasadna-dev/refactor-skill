package com.shop;
import javax.persistence.*;
@Entity
@Table(name = "products")
public class Product {
    @Id private Long id;
    private String name;
}
