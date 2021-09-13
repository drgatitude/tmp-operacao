class Card:
	"""docstring for Portal"""
	def __init__(self, empreendimento="", nomeCpf="", modalidade="", dataRetorno="", renda="", nome="", desc="", etiqueta="", construtora="", regional="", numContrato="", nomeLista="", imobiliaria="", dtEtapaAtual="", url=""):
		self.empreedimento = empreendimento
		self.nomeCpf = nomeCpf
		self.modalidade = modalidade
		self.dataRetorno = dataRetorno
		self.renda = renda
		self.nome = nome
		self.etiqueta = etiqueta
		self.construtora = construtora
		self.regional = regional
		self.numContrato = numContrato
		self.nomeLista = nomeLista
		self.imobiliaria = imobiliaria
		self.dtEtapaAtual = dtEtapaAtual
		self.url = url
		self.desc = desc

	def set_url(self):
		self.url = "https://atitudesf.portalderepasse.com.br/v3/contrato_detalhe.asp?contrato={}".format(str(self.numContrato))
		return
	def set_desc(self):
		self.desc = "Renda do cliente: R${}\n\nData de retorno: {}\n\n{}".format(str(self.renda), str(self.dataRetorno), str(self.url))
		return