import '../datasources/abstract/affiliate_data_source.dart';
import '../models/affiliate_product.dart';
import 'discovery/discovery_service.dart';
import 'product_search_service.dart';

class CatalogService implements AffiliateDataSource {
  const CatalogService();

    @override
  Future<List<AffiliateProduct>> getProducts() async {
    final products =
      await const DiscoveryService().loadFeaturedProducts();

    final result = products
        .map(
          (e) => AffiliateProduct.fromJson(
            e,
          ),
        )
        .toList();

    result.sort(
      (a, b) => b.miniBossScore.compareTo(
        a.miniBossScore,
      ),
    );

    return result;
  }

  Future<List<AffiliateProduct>> getCategory(
    String category,
  ) async {
    final products = await const DiscoveryService().loadProducts(
      category,
    );

    final result = products
        .map(
          (e) => AffiliateProduct.fromJson(
            e,
          ),
        )
        .toList();

    result.sort(
      (a, b) => b.miniBossScore.compareTo(
        a.miniBossScore,
      ),
    );

    return result;
  }

  @override
  Future<List<AffiliateProduct>> search(
    String keyword,
  ) async {
    final products = await getProducts();

    return const ProductSearchService().search(
      products,
      keyword,
    );
  }
}