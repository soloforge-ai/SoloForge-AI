import '../models/product.dart';

class MiniBossResult {
  final int score;
  final List<String> reasons;

  final String difficulty;
  final String competition;
  final String viralChance;
  final String recommendation;
  final String action;

  MiniBossResult({
    required this.score,
    required this.reasons,
    required this.difficulty,
    required this.competition,
    required this.viralChance,
    required this.recommendation,
    required this.action,
  });
}

class MiniBossEngine {
  static MiniBossResult analyze(Product product) {
    int score = 0;
    List<String> reasons = [];

    //------------------------
    // Commission
    //------------------------

    if (product.commission >= 20) {
      score += 40;
      reasons.add("💰 Excellent Commission");
    } else if (product.commission >= 15) {
      score += 35;
      reasons.add("💰 High Commission");
    } else if (product.commission >= 10) {
      score += 25;
      reasons.add("💵 Good Commission");
    }
    if (product.giftable) {
      score += 3;
      reasons.add("Great Gift Item");
    }

    //------------------------
    // Rating
    //------------------------

    if (product.rating >= 4.9) {
      score += 30;
      reasons.add("⭐ Excellent Rating");
    } else if (product.rating >= 4.7) {
      score += 25;
      reasons.add("🌟 Highly Rated");
    } else if (product.rating >= 4.5) {
      score += 20;
      reasons.add("👍 Good Rating");
    }
    if (product.evergreen) {
      score += 5;
      reasons.add("Evergreen Product");
    }
    //------------------------
    // Price
    //------------------------

    if (product.price <= 100) {
      score += 20;
      reasons.add("🔥 Easy to Sell");
    } else if (product.price <= 300) {
      score += 15;
      reasons.add("💸 Affordable");
    } else if (product.price <= 800) {
      score += 8;
      reasons.add("🛒 Mid Price");
    }

    //------------------------
    // Category
    //------------------------

    switch (product.category) {
      case "Beauty":
        score += 15;
        reasons.add("💄 Viral Category");
        break;

      case "Shopee Food":
        score += 12;
        reasons.add("🍔 Popular");
        break;

      case "Squishy":
        score += 12;
        reasons.add("🎁 Giftable");
        break;

      case "Home Decor":
        score += 10;
        reasons.add("🏠 Home Trend");
        break;

      default:
        score += 5;
    }

    if (score > 100) score = 100;

    //---------------------------------
    // AI Recommendation
    //---------------------------------

    String difficulty;
    String competition;
    String viralChance;
    String recommendation;
    String action;

    if (score >= 90) {
      difficulty = "🟢 Very Easy";
      competition = "🟢 Low";
      viralChance = "🔥 Very High";
      recommendation = "⭐⭐⭐⭐⭐ Strong Buy";
      action = "Create content today";
    } else if (score >= 75) {
      difficulty = "🟢 Easy";
      competition = "🟡 Medium";
      viralChance = "🚀 High";
      recommendation = "⭐⭐⭐⭐ Worth Selling";
      action = "Create content this week";
    } else if (score >= 60) {
      difficulty = "🟡 Medium";
      competition = "🟠 High";
      viralChance = "📈 Medium";
      recommendation = "⭐⭐⭐ Consider";
      action = "Test before promoting";
    } else {
      difficulty = "🔴 Hard";
      competition = "🔴 Very High";
      viralChance = "📉 Low";
      recommendation = "⭐⭐ Not Recommended";
      action = "Skip this product";
    }

    return MiniBossResult(
      score: score,
      reasons: reasons,
      difficulty: difficulty,
      competition: competition,
      viralChance: viralChance,
      recommendation: recommendation,
      action: action,
    );
  }
}