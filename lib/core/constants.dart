class ApiConstants {
  // Replace with your actual backend URL or local IP address (e.g., http://192.168.1.5:8000)
  // For Android emulator pointing to local machine, use: http://10.0.2.2:8000
  // For actual devices on local Wi-Fi, use your machine's local IP: http://192.168.x.x:8000
  static const String baseUrl = 'https://fortress-backend-q3l0.onrender.com/api/v1';

  // Auth Endpoints
  static const String loginEndpoint = '/auth/login';

  // Mailbox Endpoints
  static const String inboxEndpoint = '/mailbox/inbox';
  static const String respondEndpoint = '/mailbox/respond';
  static const String createRequestEndpoint = '/mailbox/create-request';
  static const String ngoRaiseRequestEndpoint = '/mailbox/ngo-raise-request';

  // Construct full URL
  static String getFullUrl(String endpoint) {
    return '$baseUrl$endpoint';
  }
}
