import { openHands } from "../open-hands-axios";

/**
 * Email Service API - Handles all email-related API endpoints
 */
class EmailService {
  /**
   * Resend email verification to the user's registered email address
   * @param userId - Optional user ID to send verification email for
   * @param isAuthFlow - Whether this is part of the authentication flow
   * @returns The response message indicating the email was sent
   */
  static async resendEmailVerification(
    userId?: string | null,
    isAuthFlow?: boolean,
  ): Promise<{ message: string }> {
    const body: { user_id?: string; is_auth_flow?: boolean } = {};
    if (userId) {
      body.user_id = userId;
    }
    if (isAuthFlow !== undefined) {
      body.is_auth_flow = isAuthFlow;
    }
    const { data } = await openHands.put<{ message: string }>(
      "/api/email/resend",
      body,
      { withCredentials: true },
    );
    return data;
  }
}

export default EmailService;
