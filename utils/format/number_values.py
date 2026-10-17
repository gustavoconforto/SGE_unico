def clean_cpf(cpf: str) -> str:
    formatted_cpf = cpf.strip().replace(".", "").replace("-","")
    
    return formatted_cpf

def format_cpf(cpf: str) -> str:
    if len(cpf) != 11:
        raise TypeError
    formatted_cpf = f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    return formatted_cpf

def clean_zip_code(zip_code: str) -> str:
    formatted_zip_code = zip_code.strip().replace(".", "").replace("-","")
    
    return formatted_zip_code

def format_zip_code(zip_code: str) -> str:
    formatted_zip_code = f"{zip_code[:-3]}-{zip_code[-3:]}"

    return formatted_zip_code
