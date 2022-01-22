


def get_fake_type(template_type: str) -> str:
  return template_type.replace('<', '_ANGLE_BRACKET_BEG_') \
                      .replace('>', '_ANGLE_BRACKET_END_') \
                      .replace('::', '_DOUBLE_COLON_') \
                      .replace(' ', '_SPACE_')

def get_orig_type(fake_type: str) -> str:
  return fake_type.replace('_ANGLE_BRACKET_BEG_', '<') \
                  .replace('_ANGLE_BRACKET_END_', '>') \
                  .replace('_DOUBLE_COLON_', '::') \
                  .replace('_SPACE_', ' ')