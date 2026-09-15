import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  const ApiException(this.message, {this.unauthorized = false});
  final String message;
  final bool unauthorized;
}

class Profile {
  const Profile({
    required this.displayName,
    required this.role,
    required this.city,
  });
  final String displayName;
  final String role;
  final String city;
  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
    displayName: json['display_name'] as String,
    role: json['role'] as String,
    city: json['city'] as String,
  );
  Map<String, String> toJson() => {
    'display_name': displayName.trim(),
    'role': role,
    'city': city.trim(),
  };
}

class InfirmoApi {
  InfirmoApi({http.Client? client, String? baseUrl})
    : _client = client ?? http.Client(),
      _baseUrl =
          (baseUrl ??
                  const String.fromEnvironment(
                    'API_BASE_URL',
                    defaultValue: '/api',
                  ))
              .replaceFirst(RegExp(r'/$'), '');
  final http.Client _client;
  final String _baseUrl;
  String? _token;

  Future<Map<String, dynamic>> _request(
    String method,
    String path, [
    Map<String, String>? body,
  ]) async {
    try {
      final request = http.Request(method, Uri.parse('$_baseUrl$path'));
      request.headers['Content-Type'] = 'application/json';
      if (_token != null) request.headers['Authorization'] = 'Bearer $_token';
      if (body != null) request.body = jsonEncode(body);
      final response = await _client
          .send(request)
          .then(http.Response.fromStream)
          .timeout(const Duration(seconds: 15));
      if (response.statusCode == 401) {
        _token = null;
        throw ApiException(
          path == '/auth/login'
              ? 'Adresse e-mail ou mot de passe incorrect.'
              : 'Session expirée. Reconnectez-vous.',
          unauthorized: true,
        );
      }
      if (response.statusCode >= 400) {
        throw ApiException(
          response.statusCode == 422
              ? 'Vérifiez les informations saisies.'
              : 'Service indisponible. Réessayez dans un instant.',
        );
      }
      return response.body.isEmpty
          ? {}
          : jsonDecode(response.body) as Map<String, dynamic>;
    } on ApiException {
      rethrow;
    } on TimeoutException {
      throw const ApiException(
        'Le serveur met trop de temps à répondre. Réessayez.',
      );
    } catch (_) {
      throw const ApiException(
        'Connexion au serveur impossible. Vérifiez votre connexion et réessayez.',
      );
    }
  }

  Future<void> login(String email, String password) async {
    _token = null;
    final result = await _request('POST', '/auth/login', {
      'email': email.trim(),
      'password': password,
    });
    if (result['access_token'] is! String ||
        (result['access_token'] as String).isEmpty) {
      throw const ApiException('Réponse de connexion invalide. Réessayez.');
    }
    _token = result['access_token'] as String;
  }

  Future<Profile> profile() async =>
      Profile.fromJson(await _request('GET', '/profile'));
  Future<Profile> save(Profile profile) async =>
      Profile.fromJson(await _request('PUT', '/profile', profile.toJson()));
  Future<void> logout() async {
    await _request('POST', '/auth/logout');
    _token = null;
  }

  void close() {
    _token = null;
    _client.close();
  }
}
