import '../../services/catalog_service.dart';

/// Backward-compatible alias that now reads from the real Shopee catalog.
@Deprecated('Use CatalogService instead.')
class MockDataSource extends CatalogService {
  /// Creates a catalog-backed data source.
  const MockDataSource();
}
