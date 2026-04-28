import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../core/constants.dart';

class ApiService {
  static const String _tokenKey = 'jwt_token';
  static const String _roleKey = 'user_role';
  static const String _nameKey = 'user_name';

  // --- Auth Management ---
  static Future<void> saveToken(String token, String role, String name) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_roleKey, role);
    await prefs.setString(_nameKey, name);
  }

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  static Future<Map<String, String?>> getUserData() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'role': prefs.getString(_roleKey),
      'name': prefs.getString(_nameKey),
    };
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_roleKey);
    await prefs.remove(_nameKey);
  }

  // --- API Headers ---
  static Future<Map<String, String>> _getHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // --- Endpoints ---

  // 1. Login Handshake
  static Future<Map<String, dynamic>> login(String phone, String pin) async {
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl(ApiConstants.loginEndpoint)),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone': phone, 'pin': pin}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await saveToken(data['access_token'], data['user']['role'], data['user']['name']);
      return data;
    } else {
      throw Exception('Login failed: ${response.body}');
    }
  }

  // --- Registration Flow ---

  // 1.1 Preflight (Check if email/phone exists)
  static Future<Map<String, dynamic>> preflight(String email, String phone) async {
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl('/auth/register/preflight')),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'phone': phone}),
    );
    return jsonDecode(response.body);
  }

  // 1.2 Verify NGO (Check Reg No)
  static Future<Map<String, dynamic>> verifyNGO(String ngoRegNo) async {
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl('/auth/verify/ngo')),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'ngo_reg_no': ngoRegNo}),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('NGO Verification failed: ${response.body}');
  }

  // 1.3 Signup NGO Admin
  static Future<Map<String, dynamic>> signupNGOAdmin(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl('/auth/register/ngo-admin')),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('NGO Signup failed: ${response.body}');
  }

  // 1.4 Signup Volunteer
  static Future<Map<String, dynamic>> signupVolunteer(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl('/auth/register/volunteer')),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Volunteer Signup failed: ${response.body}');
  }

  // 1.5 Signup Citizen
  static Future<Map<String, dynamic>> signupCitizen(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl('/auth/register/citizen')),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Citizen Signup failed: ${response.body}');
  }

  // 1.6 Setup PIN (Final Step of Registration)
  static Future<void> setupPIN(String uid, String pin) async {
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl('/auth/setup/pin')),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'uid': uid, 'pin': pin}),
    );
    if (response.statusCode != 200) {
      throw Exception('PIN Setup failed: ${response.body}');
    }
  }

  // 2. Fetch Inbox
  static Future<Map<String, dynamic>> fetchInbox() async {
    final headers = await _getHeaders();
    final response = await http.get(
      Uri.parse(ApiConstants.getFullUrl(ApiConstants.inboxEndpoint)),
      headers: headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to fetch inbox: ${response.body}');
    }
  }

  // 3. Respond to Card
  static Future<void> respondToCard(String cardId, String responseAction) async {
    final headers = await _getHeaders();
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl(ApiConstants.respondEndpoint)),
      headers: headers,
      body: jsonEncode({
        'card_id': cardId,
        'response': responseAction, // 'ACCEPT' or 'REJECT'
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to respond to card: ${response.body}');
    }
  }

  // 4. Raise Request (Citizen)
  static Future<void> createRequest(Map<String, dynamic> payload) async {
    final headers = await _getHeaders();
    final response = await http.post(
      Uri.parse(ApiConstants.getFullUrl(ApiConstants.createRequestEndpoint)),
      headers: headers,
      body: jsonEncode(payload),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to create request: ${response.body}');
    }
  }

  // 5. Fetch AI Report
  static Future<Map<String, dynamic>> fetchReport(String cardId) async {
    final headers = await _getHeaders();
    final response = await http.get(
      Uri.parse(ApiConstants.getFullUrl('/mailbox/card/$cardId/report')),
      headers: headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to fetch report: ${response.body}');
    }
  }
}
