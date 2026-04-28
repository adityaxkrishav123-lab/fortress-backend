/// Fortress Nodepoints
/// This file contains all the functions required to connect the frontend to the backend.
/// DO NOT add logic here yet. These are placeholders for manual connection.

class Nodepoints {
  // --- NGO ADMIN NODES ---
  
  /// Called when the NGO Admin clicks 'Verify' on Screen 5.
  /// Pass Aadhar, PAN, and certificate data here.
  static Future<bool> verifyAdminIdentity({
    required String aadharNo,
    required String panNo,
    required int tier,
    String? cert12AUrl,
    String? cert80GUrl,
  }) async {
    // Connect to your verification logic / Firestore checks
    return true; 
  }

  /// Final registration call from Screen 6.
  /// Includes all details from Screen 3, 5, and 6.
  static Future<void> registerNGOAdmin({
    required String name,
    required String contact,
    required String email,
    required String ngoName,
    required String ngoMail,
    required String ngoContact,
    required String region,
    required int tier,
    required String ngoType,
    required List<String> ngoTags,
    required String pin,
  }) async {
    // Connect to /api/v1/auth/register/ngo-admin
    // Then call /api/v1/auth/setup/pin
  }

  // --- MEMBER NODES ---
  
  /// Final registration call from Screen 9.
  static Future<void> registerNGOMember({
    required String name,
    required String contact,
    required String email,
    required String referralCode,
    required String pin,
  }) async {
    // Connect to /api/v1/auth/register/member
  }

  // --- CITIZEN & VOLUNTEER NODES ---

  static Future<void> registerVolunteer({
    required String name,
    required String contact,
    required String email,
    required String region,
    required String profession,
    required String aadharNo,
    String? aadharCertUrl,
    required String pin,
  }) async {
    // Connect to /api/v1/auth/register/volunteer
  }

  static Future<void> registerCitizen({
    required String name,
    required String contact,
    required String email,
    required String address,
    required String region,
    required String aadharNo,
    String? aadharCertUrl,
    required String pin,
  }) async {
    // Connect to /api/v1/auth/register/citizen
  }

  // --- SHARED NODES ---

  static Future<bool> loginWithPIN(String pin) async {
    // Connect to /api/v1/auth/login
    return true;
  }

  static Future<String?> uploadDocument(String folder, dynamic file) async {
    // Connect to your Firebase Storage upload logic
    // Return the download URL
    return "https://storage.googleapis.com/...";
  }
}
