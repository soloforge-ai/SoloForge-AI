import '../models/product.dart';
import 'catalog_service.dart';

class ProductService {
  static const CatalogService _catalogService = CatalogService();

  static Future<List<Product>> loadProducts() async {
    final affiliateProducts = await _catalogService.getProducts();

    return affiliateProducts.map((product) => product.toProduct()).toList();
  }
}
