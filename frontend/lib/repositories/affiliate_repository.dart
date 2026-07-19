import '../datasources/abstract/affiliate_data_source.dart';
import '../models/affiliate_product.dart';

/// Repository that exposes affiliate products to application features.
///
/// The repository depends on the [AffiliateDataSource] abstraction so data
/// providers can be swapped without changing feature code.
class AffiliateRepository {
  /// Creates a repository backed by [dataSource].
  const AffiliateRepository({required AffiliateDataSource dataSource})
      : _dataSource = dataSource;

  final AffiliateDataSource _dataSource;

  /// Returns affiliate products from the configured data source.
  Future<List<AffiliateProduct>> getProducts() => _dataSource.getProducts();

  /// Searches affiliate products through the configured data source.
  Future<List<AffiliateProduct>> search(String keyword) =>
      _dataSource.search(keyword);
}
