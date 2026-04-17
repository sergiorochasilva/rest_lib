import re
import uuid

from rest_lib.descriptor.dto_field import DTOField


class DTOFieldValidators:

    def validate_cpf_or_cnpj(self, dto_field: DTOField, value):
        """
        Valida se é um CPF ou CNPJ.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{dto_field.storage_name} deve ser do tipo string. Valor recebido: {value}.")

        value = self._enforce_alphanumeric_chars(value)

        if len(value) == 11:
            return self.validate_cpf(dto_field, value)
        elif len(value) == 14:
            return self.validate_cnpj(dto_field, value)

    def validate_cpf(self, dto_field: DTOField, value):
        """
        Valida se é um CPF.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{dto_field.storage_name} deve ser do tipo string. Valor recebido: {value}.")

        value = self._enforce_numeric_chars(value)

        if self._is_cpf(value):
            return value
        else:
            raise ValueError(
                f"{dto_field.storage_name} deve ser um CPF. Valor recebido: {value}.")

    def validate_cnpj(self, dto_field: DTOField, value):
        """
        Valida se é um CNPJ.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{dto_field.storage_name} deve ser do tipo string. Valor recebido: {value}.")

        value = self._enforce_alphanumeric_chars(value)

        if self._is_cnpj(value):
            return value.upper()
        else:
            raise ValueError(
                f"{dto_field.storage_name} deve ser um CNPJ. Valor recebido: {value}.")

    def validate_uuid(self, dto_field: DTOField, value):
        """
        Valida se é um UUID.
        """

        if value is None:
            return None

        if isinstance(value, uuid.UUID):
            return value

        if not isinstance(value, str):
            raise ValueError(
                f"{dto_field.storage_name} deve ser um UUID ou string correspondente. Valor recebido: {value}.")

        value = value.strip()

        if self._is_uuid(value):
            return uuid.UUID(value)
        else:
            raise ValueError(
                f"{dto_field.storage_name} deve ser um UUID. Valor recebido: {value}.")

    def validate_email(self, dto_field: DTOField, value):
        """
        Valida se é um UUID.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{dto_field.storage_name} deve ser do tipo string. Valor recebido: {value}.")

        value = value.strip()

        if self._is_email(value):
            return value
        else:
            raise ValueError(
                f"{dto_field.storage_name} deve ser um e-mail válido. Valor recebido: {value}.")

    ######################
    # Métodos Auxiliares #
    ######################

    def _enforce_numeric_chars(self, value):
        return re.sub("[^0-9]", "", value)

    def _enforce_alphanumeric_chars(self, value):
        return re.sub("[^0-9A-Za-z]", "", value)

    def _is_cpf(self, cpf: str) -> bool:
        """ If cpf in the Brazilian format is valid, it returns True, otherwise, it returns False. """

        # Check if type is str
        if not isinstance(cpf, str):
            return False

        # Removing not number chars:
        cpf = self._enforce_numeric_chars(cpf)

        # Verify if CPF number is equal
        if cpf in [
            "12345678909",
            "11111111111",
            "22222222222",
            "33333333333",
            "44444444444",
            "55555555555",
            "66666666666",
            "77777777777",
            "88888888888",
            "99999999999",
        ]:
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

    def _is_cnpj(self, cnpj: str) -> bool:
        """ 
        Method to validate brazilian cnpjs
        """

        # defining some variables
        lista_validacao_um = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        lista_validacao_dois = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        # Removing not number chars:
        cnpj = self._enforce_alphanumeric_chars(cnpj)
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

    def _is_cpf_or_cnpj(self, cpf_cnpj: str) -> bool:
        """
        Validate a brazilian CPF ou CNPJ.
        """
        if len(cpf_cnpj) == 11:
            return self._is_cpf(cpf_cnpj)
        elif len(cpf_cnpj) == 14:
            return self._is_cnpj(cpf_cnpj)
        else:
            return False

    def _is_uuid(self, value: str) -> bool:
        """
        Validate a UUID or UUID in string
        """
        value = str(value)

        if len(value) != 36:
            return False

        pattern = '^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$'
        return re.search(pattern, value) is not None

    def _is_email(self, value: str) -> bool:
        """
        Validate a email in string
        """
        value = str(value)

        pattern = '^[^@\n]+@[^@\n]+(\.[^@\n]+)+$'
        return re.search(pattern, value) is not None