import re


def validate_cpf(cpf: str) -> bool:
    """ If cpf in the Brazilian format is valid, it returns True, otherwise, it returns False. """

    # Check if type is str
    if not isinstance(cpf, str):
        return False

    # Remove some unwanted characters
    cpf = re.sub("[^0-9]", '', cpf)

    # Verify if CPF number is equal
    if cpf in ['12345678909', '00000000000', '11111111111', '22222222222', '33333333333', '44444444444', '55555555555', '66666666666', '77777777777', '88888888888', '99999999999']:
        return False

    # Checks if string has 11 characters
    if len(cpf) != 11:
        return False

    sum = 0
    weight = 10

    """ Calculating the first cpf check digit. """
    for n in range(9):
        sum = sum + int(cpf[n]) * weight

        # Decrement weight
        weight = weight - 1

    verifyingDigit = 11 - sum % 11

    if verifyingDigit > 9:
        firstVerifyingDigit = 0
    else:
        firstVerifyingDigit = verifyingDigit

    """ Calculating the second check digit of cpf. """
    sum = 0
    weight = 11
    for n in range(10):
        sum = sum + int(cpf[n]) * weight

        # Decrement weight
        weight = weight - 1

    verifyingDigit = 11 - sum % 11

    if verifyingDigit > 9:
        secondVerifyingDigit = 0
    else:
        secondVerifyingDigit = verifyingDigit

    if cpf[-2:] == "%s%s" % (firstVerifyingDigit, secondVerifyingDigit):
        return True
    return False


def validate_cnpj(cnpj: str) -> bool:
    """ 
    Method to validate brazilian cnpjs
    """

    # defining some variables
    lista_validacao_um = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    lista_validacao_dois = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    # cleaning the cnpj
    cnpj = cnpj.replace("-", "")
    cnpj = cnpj.replace(".", "")
    cnpj = cnpj.replace("/", "")
    cnpj = cnpj.upper()

    # finding out the digits
    verificadores = cnpj[-2:]

    # verifying the lenght of the cnpj
    if len(cnpj) != 14:
        return False

    # calculating the first digit
    soma = 0
    id = 0
    for numero in cnpj:

        # to do not raise indexerrors
        try:
            lista_validacao_um[id]
        except:
            break

        soma += (numero.encode("ascii")[0] - 48) * int(lista_validacao_um[id])
        id += 1

    soma = soma % 11
    if soma < 2:
        digito_um = 0
    else:
        digito_um = 11 - soma

    # converting to string, for later comparison
    digito_um = str(digito_um)

    # calculating the second digit
    # suming the two lists
    soma = 0
    id = 0

    # suming the two lists
    for numero in cnpj:

        # to do not raise indexerrors
        try:
            lista_validacao_dois[id]
        except:
            break

        soma += (numero.encode("ascii")[0] - 48) * int(lista_validacao_dois[id])
        id += 1

    # defining the digit
    soma = soma % 11
    if soma < 2:
        digito_dois = 0
    else:
        digito_dois = 11 - soma

    digito_dois = str(digito_dois)

    # returnig
    return bool(verificadores == digito_um + digito_dois)


def validate_cpf_cnpj(cpf_cnpj: str) -> bool:
    """
    Validate a brazilian CPF ou CNPJ.
    """

    if len(cpf_cnpj) == 11:
        return validate_cpf(cpf_cnpj)
    elif len(cpf_cnpj) == 14:
        return validate_cnpj(cpf_cnpj)
    else:
        return False


def add_mascara_cpf_cnpj(doc: str) -> str:
    """
    Valida o tamanho do CPF/CNPJ, e retorna já com máscara.
    """

    if doc is None:
        return None

    if len(doc) == 11:
        return '{}.{}.{}-{}'.format(doc[0:3], doc[3:6], doc[6:9], doc[9:11])
    elif len(doc) == 14:
        return '{}.{}.{}/{}-{}'.format(doc[0:2], doc[2:5], doc[5:8], doc[8:12], doc[12:14])
    else:
        raise Exception(
            'Invalid CPF/CNPJ length ({}): {}'.format(len(doc), doc))


def remove_mascara_cpf_cnpj(doc: str) -> str:
    """
    Remove a máscara de um CPF/CNPJ e retorna.

    Lança erro, se o resultado não tiver um tamanho correto de string.
    """

    if doc is None:
        return None

    doc = doc.replace('.', '').replace('/', '').replace('-', '')

    if len(doc) != 11 and len(doc) != 14:
        raise Exception(
            'Invalid CPF/CNPJ: {}'.format(doc))

    return doc
