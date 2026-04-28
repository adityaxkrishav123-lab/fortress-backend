import 'package:hive_flutter/hive_flutter.dart';

/// Phase 7: Mailbox & Hive Storage Service
/// This service handles local mirroring of "Answered" action cards
/// to reduce server load and provide offline access to logs.
class MailboxService {
  static const String _boxName = 'answered_cards_box';

  static Future<void> init() async {
    await Hive.initFlutter();
    await Hive.openBox(_boxName);
  }

  static Box get _box => Hive.box(_boxName);

  /// Saves an "Answered" card to local storage
  static Future<void> saveToLocal(Map<String, dynamic> cardData) async {
    final id = cardData['id'] ?? DateTime.now().millisecondsSinceEpoch.toString();
    await _box.put(id, cardData);
  }

  /// Retrieves all locally saved cards
  static List<Map<String, dynamic>> getLocalLogs() {
    return _box.values.map((e) => Map<String, dynamic>.from(e)).toList();
  }

  /// Deletes a specific card from local storage
  static Future<void> deleteCard(String id) async {
    await _box.delete(id);
  }

  /// Manual Cleanup: Clears all local logs
  static Future<void> clearAllLogs() async {
    await _box.clear();
  }

  /// Logic: Mark as Read (Placeholder for API integration)
  static Future<void> markAllAsRead() async {
    // Call POST /api/v1/mailbox/mark-read
    // This will turn off the Dashboard Glow
    print('Nodepoint: POST /api/v1/mailbox/mark-read triggered');
  }
}
