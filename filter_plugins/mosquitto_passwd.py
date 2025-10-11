from ansible.errors import AnsibleError

def mosquitto_password_hash(passwd, salt):
  try:
    import passlib.hash
  except Exception:
    raise AnsibleError('To use this filter, you need passlib to be installed')

  # https://github.com/eclipse/mosquitto/blob/4e6fbae45ce424d2204c8b5d51b37dc5a08013bc/src/password_mosq.h#L29
  ITERATIONS = 101

  digest = passlib.hash.pbkdf2_sha512.using(salt=salt.encode("ascii"), rounds=ITERATIONS) \
                                     .hash(passwd) \
                                     .replace('pbkdf2-sha512', '7') \
                                     .replace('.', '+')

  return digest + '=='

class FilterModule(object):
  def filters(self):
    return {
      'mosquitto_password_hash': mosquitto_password_hash,
    }
