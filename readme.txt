Item image lookup
=================

O arquivo binário ``item.bin`` armazena apenas o identificador do item, o nome (CP949), 25 atributos numéricos de 32 bits e a descrição (CP949). Ele não contém nenhuma coluna ou ponteiro separado para o ícone/arte do item. Essa estrutura pode ser verificada no script ``converter.py`` que reconstrói o arquivo a partir do ``itemout.txt`` usando exatamente esses campos (ID + 25 inteiros + nome + descrição) e nenhum campo extra para imagem.

Para exibir o ícone no cliente, o ID do item é usado diretamente como chave do arquivo de imagem. Cada ícone fica em um recurso externo (por exemplo, arquivos ``*.dds`` ou ``*.png`` do cliente) cujo nome corresponde ao ID numérico do item. Assim, ao montar a interface, o cliente pega o ``itemid`` do registro carregado do ``item.bin``, converte para string e abre o arquivo de imagem com o mesmo nome dentro do diretório de ícones.

Resumidamente: não há tabela de mapeamento adicional dentro do ``item.bin``; o vínculo entre item e imagem é feito por convenção de nome de arquivo, onde o ``itemid`` define o nome do ícone que o cliente deve carregar.
