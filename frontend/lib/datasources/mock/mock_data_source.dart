import '../abstract/affiliate_data_source.dart';
import '../../models/affiliate_product.dart';

/// In-memory affiliate data source for development and testing.
class MockDataSource implements AffiliateDataSource {
  /// Creates a mock affiliate data source.
  const MockDataSource();

  static const List<AffiliateProduct> _products = [
    AffiliateProduct(
      id: 'mock-001',
      title: 'Wireless Bluetooth Earbuds',
      imageUrl: 'https://example.com/images/earbuds.jpg',
      affiliateUrl: 'https://example.com/aff/earbuds',
      originalUrl: 'https://example.com/products/earbuds',
      price: 29.99,
      commissionRate: 8.0,
      category: 'Electronics',
      brand: 'SoundPro',
      rating: 4.7,
      sold: 15420,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-002',
      title: 'Portable Mini Blender',
      imageUrl: 'https://example.com/images/blender.jpg',
      affiliateUrl: 'https://example.com/aff/blender',
      originalUrl: 'https://example.com/products/blender',
      price: 24.50,
      commissionRate: 7.5,
      category: 'Home & Kitchen',
      brand: 'BlendGo',
      rating: 4.5,
      sold: 9821,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-003',
      title: 'Ergonomic Laptop Stand',
      imageUrl: 'https://example.com/images/laptop-stand.jpg',
      affiliateUrl: 'https://example.com/aff/laptop-stand',
      originalUrl: 'https://example.com/products/laptop-stand',
      price: 18.75,
      commissionRate: 6.0,
      category: 'Office',
      brand: 'DeskEase',
      rating: 4.8,
      sold: 7312,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-004',
      title: 'Insulated Stainless Bottle',
      imageUrl: 'https://example.com/images/bottle.jpg',
      affiliateUrl: 'https://example.com/aff/bottle',
      originalUrl: 'https://example.com/products/bottle',
      price: 15.20,
      commissionRate: 5.5,
      category: 'Sports',
      brand: 'HydraPeak',
      rating: 4.6,
      sold: 12008,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-005',
      title: 'LED Desk Lamp with USB Port',
      imageUrl: 'https://example.com/images/desk-lamp.jpg',
      affiliateUrl: 'https://example.com/aff/desk-lamp',
      originalUrl: 'https://example.com/products/desk-lamp',
      price: 22.99,
      commissionRate: 6.5,
      category: 'Home & Living',
      brand: 'BrightNest',
      rating: 4.4,
      sold: 6420,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-006',
      title: 'Fast Charging USB-C Cable',
      imageUrl: 'https://example.com/images/usb-c-cable.jpg',
      affiliateUrl: 'https://example.com/aff/usb-c-cable',
      originalUrl: 'https://example.com/products/usb-c-cable',
      price: 6.99,
      commissionRate: 9.0,
      category: 'Electronics',
      brand: 'ChargeMax',
      rating: 4.9,
      sold: 48310,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-007',
      title: 'Non-Stick Frying Pan',
      imageUrl: 'https://example.com/images/frying-pan.jpg',
      affiliateUrl: 'https://example.com/aff/frying-pan',
      originalUrl: 'https://example.com/products/frying-pan',
      price: 19.80,
      commissionRate: 5.0,
      category: 'Home & Kitchen',
      brand: 'CookMate',
      rating: 4.3,
      sold: 5305,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-008',
      title: 'Adjustable Resistance Bands',
      imageUrl: 'https://example.com/images/resistance-bands.jpg',
      affiliateUrl: 'https://example.com/aff/resistance-bands',
      originalUrl: 'https://example.com/products/resistance-bands',
      price: 13.49,
      commissionRate: 7.0,
      category: 'Fitness',
      brand: 'FlexFit',
      rating: 4.6,
      sold: 11290,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-009',
      title: 'Travel Cable Organizer',
      imageUrl: 'https://example.com/images/cable-organizer.jpg',
      affiliateUrl: 'https://example.com/aff/cable-organizer',
      originalUrl: 'https://example.com/products/cable-organizer',
      price: 9.90,
      commissionRate: 6.0,
      category: 'Travel',
      brand: 'PackWell',
      rating: 4.5,
      sold: 8844,
      rawData: {'source': 'mock'},
    ),
    AffiliateProduct(
      id: 'mock-010',
      title: 'Reusable Silicone Food Bags',
      imageUrl: 'https://example.com/images/food-bags.jpg',
      affiliateUrl: 'https://example.com/aff/food-bags',
      originalUrl: 'https://example.com/products/food-bags',
      price: 11.99,
      commissionRate: 5.5,
      category: 'Eco Living',
      brand: 'GreenLoop',
      rating: 4.2,
      sold: 4675,
      rawData: {'source': 'mock'},
    ),
  ];

  @override
  Future<List<AffiliateProduct>> getProducts() async => _products;

  @override
  Future<List<AffiliateProduct>> search(String keyword) async {
    final normalizedKeyword = keyword.trim().toLowerCase();
    if (normalizedKeyword.isEmpty) {
      return getProducts();
    }

    return _products.where((product) {
      return product.title.toLowerCase().contains(normalizedKeyword) ||
          product.category.toLowerCase().contains(normalizedKeyword) ||
          product.brand.toLowerCase().contains(normalizedKeyword);
    }).toList();
  }
}
