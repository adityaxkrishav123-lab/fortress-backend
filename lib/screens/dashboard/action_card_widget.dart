import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'dart:ui'; // For ImageFilter.blur

enum ActionCardType { instant, service, volunteer, citizen }

class ActionCard extends StatelessWidget {
  final String senderName;
  final String message;
  final ActionCardType type;
  final bool isOutgoing;
  final String? time;
  final bool isAccepted;
  final bool isObserver; // L3 Members see no buttons
  final String? contactPhone;
  final String? contactEmail;
  final VoidCallback? onAccept;
  final VoidCallback? onReject;
  final VoidCallback? onViewReport;

  const ActionCard({
    super.key,
    required this.senderName,
    required this.message,
    required this.type,
    this.isOutgoing = false,
    this.time,
    this.isAccepted = false,
    this.isObserver = false,
    this.contactPhone,
    this.contactEmail,
    this.onAccept,
    this.onReject,
    this.onViewReport,
  });

  Color _getTypeColor() {
    switch (type) {
      case ActionCardType.instant: return const Color(0xFFFF9800); // HSL Adjusted Orange
      case ActionCardType.service: return AppTheme.tealPrimary;
      case ActionCardType.volunteer: return const Color(0xFF9C27B0); // Deep Tactical Purple
      case ActionCardType.citizen: return const Color(0xFF2196F3); // Clear Blue
    }
  }

  String _getTypeLabel() {
    switch (type) {
      case ActionCardType.instant: return 'INSTANT HELP';
      case ActionCardType.service: return 'NGO SERVICE';
      case ActionCardType.volunteer: return 'VOLUNTEER';
      case ActionCardType.citizen: return 'CITIZEN SOS';
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool showContact = isAccepted || isOutgoing;

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: _getTypeColor().withOpacity(0.08),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
        border: Border.all(color: Colors.grey.withOpacity(0.1)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Status Indicator Top Bar
            Container(
              height: 4,
              width: double.infinity,
              color: _getTypeColor(),
            ),
            
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Row(
                    children: [
                      _buildAvatar(),
                      const SizedBox(width: 12),
                      Expanded(child: _buildHeaderInfo()),
                      _buildBadge(),
                    ],
                  ),
                  const SizedBox(height: 20),
                  
                  // Message Box
                  _buildMessageBox(),
                  const SizedBox(height: 16),

                  // Identity Handshake Section (Shielded Contacts)
                  _buildIdentityHandshake(showContact),
                  const SizedBox(height: 16),

                  // Attachments (Simulated)
                  _buildAttachmentRow(),
                  const SizedBox(height: 20),

                  // Actions Layer
                  _buildActionButtons(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAvatar() {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [_getTypeColor().withOpacity(0.2), _getTypeColor().withOpacity(0.05)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Text(
          senderName[0].toUpperCase(),
          style: TextStyle(
            color: _getTypeColor(),
            fontWeight: FontWeight.w900,
            fontSize: 18,
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderInfo() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          senderName,
          style: const TextStyle(
            fontWeight: FontWeight.w900,
            fontSize: 17,
            color: AppTheme.navySecondary,
            letterSpacing: -0.5,
          ),
        ),
        if (time != null)
          Text(
            time!,
            style: TextStyle(
              color: Colors.grey[500],
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
      ],
    );
  }

  Widget _buildBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: _getTypeColor().withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        _getTypeLabel(),
        style: TextStyle(
          color: _getTypeColor(),
          fontSize: 10,
          fontWeight: FontWeight.w900,
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Widget _buildMessageBox() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF8F9FB),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFEDF0F3)),
      ),
      child: Text(
        message,
        style: TextStyle(
          color: Colors.blueGrey[900],
          height: 1.5,
          fontSize: 14,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildIdentityHandshake(bool show) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: show ? AppTheme.tealPrimary.withOpacity(0.05) : Colors.grey[100],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: show ? AppTheme.tealPrimary.withOpacity(0.1) : Colors.grey[200]!,
        ),
      ),
      child: Row(
        children: [
          Icon(
            show ? Icons.verified_user : Icons.lock_person_outlined,
            size: 20,
            color: show ? AppTheme.tealPrimary : Colors.grey[500],
          ),
          const SizedBox(width: 12),
          Expanded(
            child: show
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        contactPhone ?? 'No Phone Provided',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                      Text(
                        contactEmail ?? 'No Email Provided',
                        style: TextStyle(color: Colors.grey[600], fontSize: 12),
                      ),
                    ],
                  )
                : const Text(
                    'Contact hidden until accepted',
                    style: TextStyle(
                      fontStyle: FontStyle.italic,
                      color: Colors.grey,
                      fontSize: 13,
                    ),
                  ),
          ),
          if (!show)
            Icon(Icons.info_outline, size: 16, color: Colors.grey[400]),
        ],
      ),
    );
  }

  Widget _buildAttachmentRow() {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.blue.withOpacity(0.05),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.picture_as_pdf, color: Colors.red, size: 20),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Mission_Context.pdf',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 13,
                decoration: TextDecoration.underline,
              ),
            ),
            Text(
              '1.2 MB • Tactical Attachment',
              style: TextStyle(color: Colors.grey[500], fontSize: 11),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildActionButtons() {
    if (isObserver) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: Colors.amber.withOpacity(0.05),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Center(
          child: Text(
            'READ-ONLY VIEW (OBSERVER)',
            style: TextStyle(
              color: Colors.orange,
              fontWeight: FontWeight.w900,
              fontSize: 11,
              letterSpacing: 1,
            ),
          ),
        ),
      );
    }

    if (isAccepted) {
      return SizedBox(
        width: double.infinity,
        height: 50,
        child: ElevatedButton.icon(
          onPressed: onViewReport,
          icon: const Icon(Icons.analytics_outlined, size: 20),
          label: const Text('VIEW AI MISSION REPORT'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.navySecondary,
            foregroundColor: Colors.white,
            elevation: 0,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
      );
    }

    if (isOutgoing) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: Colors.blue.withOpacity(0.05),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.blue.withOpacity(0.1)),
        ),
        child: const Center(
          child: Text(
            'WAITING FOR NGO RESPONSE...',
            style: TextStyle(
              color: Colors.blue,
              fontWeight: FontWeight.w900,
              fontSize: 12,
              letterSpacing: 1,
            ),
          ),
        ),
      );
    }

    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 48,
            child: OutlinedButton(
              onPressed: onReject,
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Color(0xFFFFEBEE), width: 2),
                foregroundColor: Colors.redAccent,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('REJECT', style: TextStyle(fontWeight: FontWeight.w900)),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: SizedBox(
            height: 48,
            child: ElevatedButton(
              onPressed: onAccept,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.tealPrimary,
                foregroundColor: Colors.white,
                elevation: 4,
                shadowColor: AppTheme.tealPrimary.withOpacity(0.4),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('ACCEPT', style: TextStyle(fontWeight: FontWeight.w900)),
            ),
          ),
        ),
      ],
    );
  }
}

