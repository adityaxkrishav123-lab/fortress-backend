import 'package:flutter/material.dart';

class AppTheme {
  // Palette - Simple & Serious
  static const Color navySecondary = Color(0xFF1A237E); // Deep Navy
  static const Color tealPrimary = Color(0xFF009688);   // Premium Teal
  static const Color primaryColor = tealPrimary;        // Alias for compatibility
  static const Color backgroundGray = Color(0xFFF5F5F5);

  // Design tokens
  static const double borderRadius = 20.0;

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Inter', // Modern tactical typography
      brightness: Brightness.light,
      colorScheme: ColorScheme.fromSeed(
        seedColor: tealPrimary,
        primary: tealPrimary,
        secondary: navySecondary,
        surface: Colors.white,
      ),
      scaffoldBackgroundColor: backgroundGray,
      textTheme: const TextTheme(
        headlineMedium: TextStyle(color: navySecondary, fontWeight: FontWeight.bold),
        bodyLarge: TextStyle(color: Colors.black87),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: tealPrimary,
          foregroundColor: Colors.white,
          minimumSize: const Size(double.infinity, 56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(borderRadius),
          ),
          elevation: 1,
        ),
      ),
      cardTheme: CardTheme(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(borderRadius),
          side: BorderSide(color: Colors.grey.withOpacity(0.1)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadius),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadius),
          borderSide: BorderSide(color: Colors.grey.withOpacity(0.2)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadius),
          borderSide: const BorderSide(color: tealPrimary, width: 2),
        ),
      ),
    );
  }

}
