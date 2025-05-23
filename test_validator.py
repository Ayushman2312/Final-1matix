from data_miner.improved_validators import validate_email, validate_indian_phone

def test_email_validator():
    # Test false positives that should be rejected
    false_positives = [
        'm@erial.our',
        'applic@ion.they',
        'loc@ion-srch.svg',
        'related-c@-wrapper.card',
        'mc@-revamp-mic.svg',
        'aerial-work-pl@form.html',
        'mc@-product-video-cont.more',
        'verific@ion.html',
        'autom@ic-labelling-machine.html',
        'tiimg.tist@ic.com',
        'cpimg.tist@ic.com',
        'air-compressors-air-separ@ion-plants',
        'return-cancell@ion-policy.html',
        'semi-autom@ic-pp-sheet-extruder',
        'stamps-st@us.ti',
        'applic@ions.they',
        'm@erial-handling-equipment',
        'tradekh@a.tradeindia.com',
        'industrial-vibr@ing-screen.html',
        'st.tist@ic.com',
        'specific@ion.we',
        'sl@-conveyors.html',
        'kolk@a.you',
        'basm@i-rice.html',
        'product-specific@ion'
    ]
    
    print("Testing email validation for false positives (should all be rejected):")
    for i, email in enumerate(false_positives, 1):
        result = validate_email(email)
        print(f"{i:2}. {email:<40} - {'❌ REJECTED' if not result else '⚠️ WRONGLY ACCEPTED'}")
    
    # Test real emails that should be accepted
    real_emails = [
        'contact@example.com',
        'support@company.co.in',
        'info@domain.in',
        'user.name@gmail.com',
        'business@outlook.com',
        'sales@indiancompany.in',
        'helpdesk@techfirm.com',
        'john.doe@company.net',
        'contact@business-name.com',
        'info@company-name.in'
    ]
    
    print("\nTesting email validation for real emails (should all be accepted):")
    for i, email in enumerate(real_emails, 1):
        result = validate_email(email)
        print(f"{i:2}. {email:<40} - {'✅ ACCEPTED' if result else '⚠️ WRONGLY REJECTED'}")

def test_phone_validator():
    # Test valid Indian phone numbers
    valid_phones = [
        '+919876543210',
        '9876543210',
        '+91 98765 43210',
        '98765-43210',
        '09876543210',
        '(+91)9876543210',
        '+91-98765-43210'
    ]
    
    print("\nTesting phone validation for valid Indian numbers (should all be accepted):")
    for i, phone in enumerate(valid_phones, 1):
        result = validate_indian_phone(phone)
        print(f"{i:2}. {phone:<20} - {'✅ ACCEPTED' if result else '⚠️ WRONGLY REJECTED'} - {result}")
    
    # Test invalid phone numbers that should be rejected
    invalid_phones = [
        '1234567890',  # Doesn't start with 6-9
        '5432167890',  # Doesn't start with 6-9
        '123456',      # Too short
        '9999999999',  # All same digits
        '1234567890',  # Sequential pattern
        '91123456789'  # Invalid after country code
    ]
    
    print("\nTesting phone validation for invalid numbers (should all be rejected):")
    for i, phone in enumerate(invalid_phones, 1):
        result = validate_indian_phone(phone)
        print(f"{i:2}. {phone:<20} - {'❌ REJECTED' if not result else '⚠️ WRONGLY ACCEPTED'} - {result}")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING IMPROVED EMAIL AND PHONE VALIDATION")
    print("=" * 60)
    test_email_validator()
    test_phone_validator()
    print("\nValidation testing complete.") 