# AI Analytics Platform - Security Checklist

## API Key Security (CRITICAL)

### ✅ Environment Variables
- [ ] API keys in `.env` file only
- [ ] `.env` in `.gitignore` (never committed)
- [ ] Different keys for dev/staging/prod
- [ ] Keys rotated monthly

### ✅ Key Management
```bash
# Generate secure secret
openssl rand -hex 32

# Never do this:
❌ api_key = "sk-123..."  # Hardcoded
❌ print(api_key)          # Logging keys
❌ return api_key          # API responses

# Always do this:
✅ api_key = os.getenv("KIMI_API_KEY")
✅ logger.info("API call made")  # No key in logs
✅ return {"status": "success"}  # Sanitized response
```

### ✅ Production Security (Future)
- [ ] AWS Secrets Manager or Doppler
- [ ] Secrets injected at runtime
- [ ] Key access audit logging
- [ ] Automatic key rotation
- [ ] IP allowlisting

---

## Database Security

### ✅ Connection Security
- [ ] SSL/TLS enforced
- [ ] Connection string in env var only
- [ ] Read-only credentials for app
- [ ] Separate write credentials for migrations

### ✅ SQL Injection Prevention
```python
# ❌ Never:
cursor.execute(f"SELECT * FROM {table}")

# ✅ Always:
cursor.execute("SELECT * FROM %s", (table,))
```

### ✅ Row-Level Security (Multi-tenant)
```sql
-- Enable RLS
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

---

## Application Security

### ✅ Input Validation
- [ ] All user inputs sanitized
- [ ] SQL keywords blocked
- [ ] Maximum query length enforced
- [ ] Rate limiting on API endpoints

### ✅ Authentication (When Enabled)
- [ ] JWT tokens with short expiry
- [ ] Refresh token rotation
- [ ] Password hashing (bcrypt)
- [ ] MFA for admin accounts

### ✅ CORS & CSRF
- [ ] CORS restricted to known origins
- [ ] CSRF tokens for state-changing ops
- [ ] SameSite cookies

---

## Infrastructure Security

### ✅ Docker Security
```dockerfile
# ❌ Never run as root
USER root

# ✅ Always create non-root user
RUN useradd -m appuser
USER appuser
```

### ✅ Network Security
- [ ] Internal services not exposed
- [ ] Database not accessible from internet
- [ ] Redis protected with password
- [ ] Firewall rules configured

---

## Monitoring & Incident Response

### ✅ Logging
- [ ] All API calls logged (without keys)
- [ ] Failed authentication attempts tracked
- [ ] Database query performance monitored
- [ ] Error tracking (Sentry)

### ✅ Alerts
- [ ] Unusual API usage patterns
- [ ] Failed login attempts >5/minute
- [ ] Database connection errors
- [ ] High error rates

### ✅ Incident Response
```
1. Detect: Automated alerts
2. Contain: Rotate compromised keys
3. Investigate: Review logs
4. Recover: Deploy fixes
5. Post-mortem: Document learnings
```

---

## Security Audit Checklist

**Before Production:**
- [ ] Penetration test
- [ ] Dependency vulnerability scan
- [ ] Code security review
- [ ] Infrastructure security review
- [ ] Compliance check (GDPR, SOC2)

**Ongoing:**
- [ ] Weekly dependency updates
- [ ] Monthly security review
- [ ] Quarterly penetration test
- [ ] Annual compliance audit

---

## Quick Security Test

```bash
# 1. Check no keys in code
grep -r "sk-" --include="*.py" --include="*.ts" .

# 2. Check .env is gitignored
git check-ignore -v backend/.env

# 3. Verify SQL injection protection
# Try: "'; DROP TABLE users; --" in query box
# Should: Return error, not execute

# 4. Check rate limiting
for i in {1..100}; do curl http://localhost:8000/api/query; done
# Should: Block after threshold
```

---

## Emergency Contacts

If security incident:
1. Rotate API keys immediately
2. Check access logs
3. Review recent changes
4. Notify team

---

**Security is everyone's responsibility. When in doubt, ask.**
