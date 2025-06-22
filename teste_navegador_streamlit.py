# -*- coding: utf-8 -*-
from IPython.display import display, clear_output, HTML
import ipywidgets as widgets
import re
import requests
from datetime import datetime
import traceback
import threading
import time

# ==============================================================================
# 1. FUNÇÕES AUXILIARES
# ==============================================================================
def formatar_brl(valor):
    try:
        s = f"{float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return s
    except:
        return "0,00"

def formatar_me(valor):
    try:
        return f"{float(parse_input(valor)):,.2f}"
    except:
        return "0,00"

def parse_input(valor):
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        s = re.sub(r'[^\d,.]', '', str(valor)).replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

# Objeto global para log de erros
debug_output = widgets.Output(layout={'border': '1px solid red', 'padding': '5px'})

# ==============================================================================
# 2. CLASSES DOS MÓDULOS
# ==============================================================================
class ModuloBase:
    def __init__(self):
        self.layout = widgets.VBox()
    def get_layout(self):
        return self.layout

class ModuloCompra(ModuloBase):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.info_operacao = widgets.HTML("<i>Aguardando preparação no Gerenciador...</i>")
        self.valor_brl_calculado = widgets.FloatText(description='Valor Calculado (R$):', disabled=True, style={'description_width': 'initial'})
        self.iof_compra = widgets.Dropdown(options=[('ISENTO', 0.0), ('0,38%', 0.0038)], value=0.0038, description='IOF:')
        self.tarifa_compra = widgets.Dropdown(options=[('ISENTO', 0.0), ('R$ 250,00', 250.0)], value=250.0, description='Tarifa:')
        self.calcular_button = widgets.Button(description='RECALCULAR', button_style='primary', icon='calculator', tooltip="Recalcular com diferentes impostos ou tarifas")
        self.limpar_button = widgets.Button(description='LIMPAR', button_style='danger', icon='trash', tooltip="Limpar os campos deste módulo")
        self.output_display = widgets.HTML()
        self.calcular_button.on_click(self.calcular)
        self.limpar_button.on_click(self.on_limpar_click)
        botoes_box = widgets.HBox([self.calcular_button, self.limpar_button])
        self.layout.children = [
            self.info_operacao,
            self.valor_brl_calculado, self.iof_compra, self.tarifa_compra,
            botoes_box, widgets.HTML("<hr>"), self.output_display
        ]
        self.limpar_state()

    def calcular(self, b):
        with debug_output:
            clear_output(wait=True)
            try:
                if self.app_ref.op_selecionada != 'COMPRA':
                    self.output_display.value = "<b style='color:red;'>Operação inválida. Prepare uma operação de COMPRA no Gerenciador.</b>"; return
                valor = self.app_ref.last_brl_value; moeda = self.app_ref.moeda_selecionada.value
                valor_me_input = self.app_ref.last_me_value; receita_operacao = self.app_ref.receita_operacao
                vet = self.app_ref.vet_calculado
                if not valor or valor <= 0: self.output_display.value = "<b style='color:red;'>Operação não preparada.</b>"; return
                iof_pct = self.iof_compra.value; tarifa = self.tarifa_compra.value
                valor_iof = valor * iof_pct; total_creditado = valor - valor_iof - tarifa
                self.output_display.value = (
                    f"<h4>RESUMO OPERAÇÃO COMPRA</h4>"
                    f"<b>Valor em Moeda Estrangeira ({moeda}):</b> {formatar_me(valor_me_input)}<br>"
                    f"<b>Valor Bruto em Reais (R$):</b> R$ {formatar_brl(valor)}<br>"
                    f"<b>V.E.T. (Custo Efetivo Total): <span style='color:purple;font-weight:bold;'>R$ {vet:.4f}</span></b><hr>"
                    f"<b>IOF ({iof_pct*100:.2f}%):</b> {'ISENTO' if valor_iof == 0 else f'- R$ {formatar_brl(valor_iof)}'}<br>"
                    f"<b>Tarifa:</b> {'ISENTO' if tarifa == 0 else f'- R$ {formatar_brl(tarifa)}'}<br><hr>"
                    f"<b>Receita da Operação: <span style='color:blue;font-weight:bold;'>R$ {formatar_brl(receita_operacao)}</span></b><br>"
                    f"<b>Valor Creditado:</b> <span style='color:green; font-weight:bold;'>R$ {formatar_brl(total_creditado)}</span>"
                )
            except Exception as e:
                print(f"Erro em ModuloCompra.calcular:\n{traceback.format_exc()}")

    def on_limpar_click(self, b):
        self.limpar_state()
        self.output_display.value = "<i>Campos do módulo de compra foram limpos.</i>"

    def limpar_state(self):
        self.info_operacao.value = "<i>Aguardando preparação no Gerenciador...</i>"
        self.valor_brl_calculado.value = 0; self.output_display.value = ""

class ModuloVenda(ModuloBase):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.info_operacao = widgets.HTML("<i>Aguardando preparação no Gerenciador...</i>")
        self.valor_brl_calculado = widgets.FloatText(description='Valor Calculado (R$):', disabled=True, style={'description_width': 'initial'})
        self.iof_venda = widgets.Dropdown(options=[('ISENTO', 0.0), ('1,10%', 0.011), ('3,5%', 0.035)], value=0.035, description='IOF:')
        self.ir_venda = widgets.Dropdown(options=[('ISENTO',0.0),('15% (CREDOR)',0.15),('17,64706% (DEVEDOR)',0.1764706)],value=0.0,description='I.R:')
        self.tarifa_venda = widgets.Dropdown(options=[('ISENTO',0.0),('R$ 250,00',250.0)],value=250.0,description='Tarifa:')
        self.calcular_button = widgets.Button(description='CALCULAR',button_style='primary',icon='calculator')
        self.limpar_button = widgets.Button(description='LIMPAR', button_style='danger', icon='trash', tooltip="Limpar os campos deste módulo")
        self.output_display = widgets.HTML()
        self.calcular_button.on_click(self.calcular)
        self.limpar_button.on_click(self.on_limpar_click)
        botoes_box = widgets.HBox([self.calcular_button, self.limpar_button])
        self.layout.children = [
            self.info_operacao,
            self.valor_brl_calculado, self.iof_venda, self.ir_venda, self.tarifa_venda,
            botoes_box, widgets.HTML("<hr>"), self.output_display
        ]
        self.limpar_state()

    def calcular(self, b):
        with debug_output:
            clear_output(wait=True)
            try:
                if self.app_ref.op_selecionada != 'VENDA':
                    self.output_display.value = f"<b style='color:red;'>Operação inválida. Prepare uma operação de VENDA no Gerenciador.</b>"; return
                valor_input = self.app_ref.last_brl_value; moeda = self.app_ref.moeda_selecionada.value
                valor_me_input = self.app_ref.last_me_value; receita_operacao = self.app_ref.receita_operacao
                vet = self.app_ref.vet_calculado
                if not valor_input or valor_input<=0: self.output_display.value="<b style='color:red;'>Operação não preparada.</b>"; return
                iof_pct=self.iof_venda.value;ir_pct=self.ir_venda.value;tarifa=self.tarifa_venda.value
                valor_base=valor_input*(1-ir_pct) if ir_pct==0.15 else valor_input
                valor_iof=valor_base * iof_pct
                valor_ir=valor_base*ir_pct if ir_pct==0.1764706 else valor_input*ir_pct
                total_operacao=valor_base+valor_iof+valor_ir+tarifa
                self.output_display.value = (
                    f"<h4>RESUMO OPERAÇÃO VENDA</h4>"
                    f"<b>Valor em Moeda Estrangeira ({moeda}):</b> {formatar_me(valor_me_input)}<br>"
                    f"<b>Valor Base (R$):</b> R$ {formatar_brl(valor_base)}<br>"
                    f"<b>V.E.T. (Custo Efetivo Total): <span style='color:purple;font-weight:bold;'>R$ {vet:.4f}</span></b><hr>"
                    f"<b>IOF ({iof_pct*100:.2f}%):</b> {'ISENTO' if valor_iof==0 else f'+ R$ {formatar_brl(valor_iof)}'}<br>"
                    f"<b>I.R.:</b> {'ISENTO' if valor_ir==0 else f'+ R$ {formatar_brl(valor_ir)}'}<br>"
                    f"<b>Tarifa:</b> {'ISENTO' if tarifa==0 else f'+ R$ {formatar_brl(tarifa)}'}<br><hr>"
                    f"<b>Receita da Operação: <span style='color:blue;font-weight:bold;'>R$ {formatar_brl(receita_operacao)}</span></b><br>"
                    f"<b>Custo Total:</b> <span style='color:red;font-weight:bold;'>R$ {formatar_brl(total_operacao)}</span>"
                )
            except Exception as e:
                print(f"Erro em ModuloVenda.calcular:\n{traceback.format_exc()}")

    def on_limpar_click(self, b):
        self.limpar_state()
        self.output_display.value = "<i>Campos do módulo de venda foram limpos.</i>"

    def limpar_state(self):
        self.info_operacao.value = "<i>Aguardando preparação no Gerenciador...</i>"
        self.valor_brl_calculado.value = 0; self.output_display.value = ""

class ModuloValorEmReais(ModuloBase):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.valor_brl = widgets.Text(description='Valor em R$:', placeholder='Ex: 10000.00')
        self.iof_dropdown = widgets.Dropdown(options=[('ISENTO', 0.0), ('1,10%', 0.011), ('3,5%', 0.035)], value=0.035, description='IOF:')
        self.ir_dropdown = widgets.Dropdown(options=[('ISENTO', 0.0), ('15% (CREDOR)', 0.15), ('17,64706% (DEVEDOR)', 0.1764706)], value=0.0, description='I.R:')
        self.tarifa_dropdown = widgets.Dropdown(options=[('ISENTO', 0.0), ('R$ 250,00', 250.0)], value=0.0, description='Tarifa:')
        self.calcular_button = widgets.Button(description='CALCULAR', button_style='success', icon='calculator')
        self.limpar_button = widgets.Button(description='LIMPAR', button_style='danger', icon='trash')
        self.output_display = widgets.HTML(value="<p><i>Insira o valor em R$ e clique em CALCULAR.</i></p>")
        self.calcular_button.on_click(self.calcular_custos)
        self.limpar_button.on_click(self.limpar)
        self.layout.children = [
            widgets.HTML("<p>Calcule os custos para um valor em reais, independente de moeda estrangeira.</p>"),
            self.valor_brl, self.iof_dropdown, self.ir_dropdown, self.tarifa_dropdown,
            widgets.HBox([self.calcular_button, self.limpar_button]), self.output_display
        ]

    def calcular_custos(self, b):
        with debug_output:
            clear_output(wait=True)
            self.output_display.value = ""
            try:
                valor_brl_conta = parse_input(self.valor_brl.value)
                if not valor_brl_conta or valor_brl_conta <= 0:
                    self.output_display.value = "<b style='color:red'>O Valor em R$ deve ser preenchido e maior que zero.</b>"
                    return
                iof_pct = self.iof_dropdown.value
                ir_pct = self.ir_dropdown.value
                tarifa = self.tarifa_dropdown.value

                valor_base = valor_brl_conta - tarifa
                if ir_pct == 0.15:
                    valor_base -= valor_brl_conta * 0.15

                divisor = 1 + iof_pct
                valor_boleto = valor_base / divisor

                valor_iof = valor_boleto * iof_pct
                valor_ir = valor_boleto * ir_pct if ir_pct == 0.1764706 else valor_brl_conta * ir_pct
                custo_total = valor_boleto + valor_iof + valor_ir + tarifa

                self.output_display.value = (
                    f"<h4>✅ Resultado</h4>"
                    f"<b>Valor na Conta:</b> R$ {formatar_brl(valor_brl_conta)}<br>"
                    f"<b>Valor do Boleto:</b> <span style='color:blue;font-weight:bold;'>R$ {formatar_brl(valor_boleto)}</span><br><hr>"
                    f"<b>Detalhes (R$):</b><br>"
                    f"Valor Base (após tarifa e IR inicial): R$ {formatar_brl(valor_base)}<br>"
                    f"IOF ({iof_pct*100:.2f}%): {'ISENTO' if valor_iof==0 else f'+ R$ {formatar_brl(valor_iof)}'}<br>"
                    f"I.R.: {'ISENTO' if valor_ir==0 else f'+ R$ {formatar_brl(valor_ir)}'}<br>"
                    f"Tarifa: {'ISENTO' if tarifa==0 else f'+ R$ {formatar_brl(tarifa)}'}<br><hr>"
                    f"<b>Custo Total:</b> <span style='color:red;font-weight:bold;'>R$ {formatar_brl(custo_total)}</span>"
                )
            except Exception as e:
                print(f"Erro em ModuloValorEmReais.calcular_custos:\n{traceback.format_exc()}")

    def limpar(self, b):
        self.valor_brl.value=""
        self.iof_dropdown.value=0.035
        self.ir_dropdown.value=0.0
        self.tarifa_dropdown.value=0.0
        self.output_display.value="<p><i>Campos limpos.</i></p>"

class ModuloConcomitante(ModuloBase):
    def __init__(self):
        super().__init__()
        self.ponta_venda_valor=widgets.Text(description='Valor Incidente:',placeholder='Ex: 10000,00')
        self.ponta_venda_ir=widgets.Dropdown(options=[('ISENTO',0.0),('15% (CREDOR)',0.15),('17,64706% (DEVEDOR)',0.1764706)],description='I.R:')
        self.ir_warning_label=widgets.HTML(value="",layout={'visibility':'hidden'})
        self.ponta_venda_iof=widgets.Dropdown(options=[('ISENTO',0.0),('1,10%',0.011),('3,5%',0.035)],description='IOF Venda:')
        self.ponta_venda_tarifa=widgets.Dropdown(options=[('ISENTO',0.0),('R$ 250,00',250.0)],description='Tarifa Venda:')
        self.ponta_compra_iof=widgets.Dropdown(options=[('0,38%',0.0038)],description='IOF Compra:')
        self.ponta_compra_tarifa=widgets.Dropdown(options=[('ISENTO',0.0),('R$ 250,00',250.0)],description='Tarifa Compra:')
        self.calcular_button=widgets.Button(description='CALCULAR',button_style='primary',icon='calculator')
        self.limpar_button=widgets.Button(description='LIMPAR',button_style='danger',icon='trash')
        self.outputs={k:widgets.HTML() for k in ["operacao","venda","compra","final"]}
        self.ponta_venda_ir.observe(self._update_ir_warning,names='value')
        self.calcular_button.on_click(self.calcular)
        self.limpar_button.on_click(self.limpar)
        self.layout.children=[widgets.HTML("<p style='font-size:11px;color:orange;'><i>Nota: Este módulo é autocontido.</i></p>"),widgets.HTML("<b>PONTA VENDA:</b>"),self.ponta_venda_valor,widgets.HBox([self.ponta_venda_ir,self.ir_warning_label]),self.ponta_venda_iof,self.ponta_venda_tarifa,widgets.HTML("<br><b>PONTA COMPRA:</b>"),self.ponta_compra_iof,self.ponta_compra_tarifa,widgets.HBox([self.calcular_button,self.limpar_button]),widgets.HTML("<hr>"),self.outputs["operacao"],widgets.HTML("<hr>"),self.outputs["venda"],widgets.HTML("<hr>"),self.outputs["compra"],widgets.HTML("<hr>"),self.outputs["final"]]
        self.limpar(None)

    def _update_ir_warning(self,c):
        self.ir_warning_label.layout.visibility='visible' if c['new']==0.1764706 else 'hidden'
        self.ir_warning_label.value="<b style='color:red;font-size:11px;'>I.R será debitado à parte.</b>"

    def calcular(self,b):
        with debug_output:
            clear_output(wait=True)
            try:
                venda_valor=parse_input(self.ponta_venda_valor.value)
                venda_ir_pct=self.ponta_venda_ir.value
                venda_iof_pct=self.ponta_venda_iof.value
                tarifa_venda=self.ponta_venda_tarifa.value
                valor_boleto_venda=venda_valor*(1-0.15) if venda_ir_pct==0.15 else venda_valor
                valor_iof_venda=valor_boleto_venda*venda_iof_pct
                tarifa_compra=self.ponta_compra_tarifa.value
                valor_total_ponta_compra=valor_iof_venda/(1-self.ponta_compra_iof.value)
                compra_valor=valor_total_ponta_compra
                valor_iof_compra=compra_valor*self.ponta_compra_iof.value
                net_iof_compra=valor_iof_venda
                valor_total_creditado=compra_valor-valor_iof_compra-tarifa_compra
                valor_ir_venda=venda_valor*venda_ir_pct
                valor_total_debitado=valor_boleto_venda+(valor_ir_venda if venda_ir_pct==0.1764706 else 0)+valor_iof_venda+tarifa_venda
                valor_total_operacao=valor_total_debitado
                valor_real_enviado=valor_boleto_venda-tarifa_venda-valor_iof_compra-tarifa_compra
                self.outputs["operacao"].value=f"<h4>VALORES DA OPERAÇÃO</h4><b>Boleto VENDA:</b> R$ {formatar_brl(valor_boleto_venda)}<br><b>Boleto COMPRA:</b> R$ {formatar_brl(compra_valor)}"
                self.outputs["venda"].value=f"<h4>RESUMO - PONTA VENDA</h4><b>I.R.:</b> R$ {formatar_brl(valor_ir_venda)}<br><b>IOF ({venda_iof_pct*100:.2f}%):</b> R$ {formatar_brl(valor_iof_venda)}<br><b>Tarifa:</b> R$ {formatar_brl(tarifa_venda)}<br><b>Total DEBITADO:</b><span style='color:red;font-weight:bold;'>R$ {formatar_brl(valor_total_debitado)}</span>"
                self.outputs["compra"].value=f"<h4>RESUMO - PONTA COMPRA</h4><b>Total Ponta Compra (GROSS UP):</b> R$ {formatar_brl(valor_total_ponta_compra)}<br><b>NET IOF COMPRA:</b><span style='color:green;'>R$ {formatar_brl(net_iof_compra)}</span><br><b>IOF Pta Compra (0,38%):</b><span style='color:red;'>R$ {formatar_brl(valor_iof_compra)}</span><br><b>Tarifa Compra:</b><span style='color:red;'>R$ {formatar_brl(tarifa_compra)}</span><br><b>Total CREDITADO:</b><span style='color:green;font-weight:bold;'>R$ {formatar_brl(valor_total_creditado)}</span>"
                self.outputs["final"].value=f"<h4>FINAL</h4><b>VALOR INCIDENTE:</b> R$ {formatar_brl(venda_valor)}<br><b>TOTAL DA OPERAÇÃO:</b><span style='color:red;'>R$ {formatar_brl(valor_total_operacao)}</span><br><b>VALOR REAL ENVIADO:</b><span style='color:green;'>R$ {formatar_brl(valor_real_enviado)}</span>"
            except Exception as e:
                for out in self.outputs.values():out.value = ""
                print(f"Erro no Módulo Concomitante:\n{traceback.format_exc()}")

    def limpar(self,b):
        self.ponta_venda_valor.value=""
        self.ponta_venda_ir.value=0.0
        self.ponta_venda_iof.value=0.0
        self.ponta_venda_tarifa.value=0.0
        self.ponta_compra_tarifa.value=0.0
        for out in self.outputs.values():out.value=""
        self.outputs["operacao"].value="<p><i>Insira os valores.</i></p>"

# ==============================================================================
# 4. APLICAÇÃO PRINCIPAL
# ==============================================================================
class CalculadoraCambioApp:
    def __init__(self):
        # --- Configurações Iniciais ---
        self.taxa_efetiva_calculada=0.0; self.op_selecionada=None; self.last_brl_value=0.0; self.last_me_value=0.0; self.receita_operacao=0.0; self.vet_calculado = 0.0
        self.app_is_running = True
        style={'description_width':'initial'}

        # --- Ticker Bar ---
        self.ticker_bar = widgets.HTML(value="<div class='ticker-bar'><div class='ticker-content'>Carregando cotações...</div></div>")

        # --- Gerenciador ---
        self.moeda_selecionada=widgets.Dropdown(options=['USD','EUR','GBP','JPY'],value='USD',description='Moeda:',style=style)
        self.valor_me = widgets.Text(description='INSIRA VALOR EM ME:',placeholder='Ex: 10000.00',style=style)
        self.spread = widgets.FloatText(description='Spread %:',value=1.5,step=0.1,style=style)
        self.compra_button = widgets.Button(description="COMPRA",button_style='success',icon='arrow-down',layout=widgets.Layout(flex='1 1 auto', width='auto'))
        self.venda_button = widgets.Button(description="VENDA",button_style='danger',icon='arrow-up',layout=widgets.Layout(flex='1 1 auto', width='auto'))
        self.taxa_display = widgets.HTML(value="<i>Preencha os dados e selecione uma operação (Compra ou Venda).</i>")
        self.gerenciador_layout=widgets.VBox([widgets.HTML("<h4>Gerenciador de Câmbio</h4>"),widgets.HBox([self.moeda_selecionada,self.valor_me]),self.spread,widgets.HBox([self.compra_button,self.venda_button]),self.taxa_display])

        # --- Módulos ---
        self.mod_compra=ModuloCompra(self)
        self.mod_venda=ModuloVenda(self)
        self.mod_valor_em_reais=ModuloValorEmReais(self)
        self.mod_concomitante=ModuloConcomitante()

        # --- Layout dos Módulos ---
        self.accordion_esquerda = widgets.Accordion(children=[self.mod_compra.get_layout(), self.mod_valor_em_reais.get_layout()])
        self.accordion_esquerda.set_title(0,'🔧 COMPRA (RECEBIMENTO)')
        self.accordion_esquerda.set_title(1,'🔧 VALOR EM REAIS')
        self.accordion_esquerda.selected_index = None
        self.accordion_direita = widgets.Accordion(children=[self.mod_venda.get_layout(), self.mod_concomitante.get_layout()])
        self.accordion_direita.set_title(0,'🔧 VENDA (ENVIO)')
        self.accordion_direita.set_title(1,'🔧 CONCOMITANTE')
        self.accordion_direita.selected_index = None
        coluna_esquerda_box = widgets.VBox([self.accordion_esquerda], layout=widgets.Layout(width='50%', border='1px solid #e0e0e0', padding='5px'))
        coluna_direita_box = widgets.VBox([self.accordion_direita], layout=widgets.Layout(width='50%', border='1px solid #e0e0e0', padding='5px'))
        self.modulos_layout = widgets.HBox([coluna_esquerda_box, coluna_direita_box])

        # --- Botões e Ações ---
        self.compra_button.on_click(self._on_compra_click)
        self.venda_button.on_click(self._on_venda_click)

        # --- Inicia a thread para atualização da ticker bar ---
        self.update_thread = threading.Thread(target=self._run_update_loop, daemon=True)
        self.update_thread.start()

    def get_ticker_css(self):
        return """
        <style>
            @keyframes ticker-scroll {
                0% { transform: translateX(0); }
                100% { transform: translateX(-50%); }
            }
            .ticker-bar {
                background-color: #00a087; /* Verde da Bloomberg Línea */
                color: white;
                padding: 10px 20px;
                display: flex;
                overflow: hidden;
                font-family: Arial, sans-serif;
                font-size: 14px;
                width: 100%;
                position: sticky;
                top: 0;
                z-index: 100;
                box-sizing: border-box;
            }
            .ticker-content {
                display: inline-flex;
                white-space: nowrap;
                animation: ticker-scroll 30s linear infinite;
            }
            .ticker-item {
                margin-right: 30px;
            }
            .ticker-item b {
                color: #ffffff;
                font-weight: bold;
            }
            .ticker-item .last {
                color: #ffffff;
                margin-right: 10px;
            }
            .ticker-item .positive {
                color: #00ff00;
            }
            .ticker-item .negative {
                color: #ff0000;
            }
            .ticker-item .neutral {
                color: #ffffff;
            }
            .ticker-item .time {
                color: #cccccc;
                font-size: 11px;
                margin-left: 5px;
            }
            .main-content {
                margin-top: 50px; /* Espaço para a ticker bar */
            }
        </style>
        """

    def _update_ticker_bar_data(self):
        moedas_a_buscar = "USD-BRL,EUR-BRL,GBP-BRL,CAD-BRL,JPY-BRL"
        api_url = f"https://economia.awesomeapi.com.br/json/last/{moedas_a_buscar}"

        ticker_items_html = ""

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            for key, moeda_info in data.items():
                nome_formatado = f"{key[:3]}/{key[3:]}"
                preco = float(moeda_info.get('bid', 0))
                variacao_abs = float(moeda_info.get('varBid', 0))
                variacao_pct = float(moeda_info.get('pctChange', 0))
                horario_str = moeda_info.get('create_date', '')

                horario = datetime.strptime(horario_str, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')

                variacao_class = 'positive' if variacao_abs >= 0 else 'negative' if variacao_abs < 0 else 'neutral'
                sinal = "+" if variacao_abs >= 0 else ""

                item_html = f"""
                <div class="ticker-item">
                    <b>{nome_formatado}</b>
                    <span class="last">R$ {preco:.4f}</span>
                    <span class="{variacao_class}">{sinal}{variacao_pct:.2f}%</span>
                    <span class="time">{horario}</span>
                </div>
                """

                ticker_items_html += item_html

            # Duplica o conteúdo para scroll contínuo
            ticker_content = ticker_items_html + ticker_items_html
            self.ticker_bar.value = f"<div class='ticker-bar'><div class='ticker-content'>{ticker_content}</div></div>"

        except Exception as e:
            error_msg = f"<div class='ticker-item' style='color:red;'>Erro ao buscar cotações: {str(e)}</div>"
            self.ticker_bar.value = f"<div class='ticker-bar'><div class='ticker-content'>{error_msg}</div></div>"
            with debug_output:
                print(f"Erro na Ticker Bar: {e}")

    def _run_update_loop(self):
        while self.app_is_running:
            self._update_ticker_bar_data()
            time.sleep(60)

    def _update_button_styles(self):
        if self.op_selecionada == 'COMPRA':
            self.compra_button.button_style='info'
            self.venda_button.button_style='danger'
        elif self.op_selecionada == 'VENDA':
            self.venda_button.button_style='info'
            self.compra_button.button_style='success'

    def _on_compra_click(self, b):
        self.op_selecionada = 'COMPRA'
        self._update_button_styles()
        self._executar_calculo_e_preparar()

    def _on_venda_click(self, b):
        self.op_selecionada = 'VENDA'
        self._update_button_styles()
        self._executar_calculo_e_preparar()

    def _executar_calculo_e_preparar(self):
        with debug_output:
            clear_output(wait=True)
            self.compra_button.disabled=True
            self.venda_button.disabled=True
            try:
                self.last_me_value = parse_input(self.valor_me.value)
                if self.last_me_value <= 0:
                    self.taxa_display.value="<b style='color:red'>Valor em Moeda Estrangeira deve ser maior que zero.</b>"
                    return

                moeda_sigla=self.moeda_selecionada.value
                moeda_par=f"{moeda_sigla}-BRL"
                self.taxa_display.value = f"<i>Buscando cotação para {moeda_sigla}...</i>"
                response=requests.get(f'https://economia.awesomeapi.com.br/json/last/{moeda_par}')
                response.raise_for_status()
                data=response.json()
                cotacao_info=data[f'{moeda_sigla}BRL']
                taxa_comercial_pura=float(cotacao_info['bid'])
                spread_percentual=self.spread.value

                if self.op_selecionada == 'COMPRA':
                    self.taxa_efetiva_calculada=taxa_comercial_pura*(1-(spread_percentual/100))
                    op_str=f"Taxa Cambial (-{spread_percentual}%)"
                    target_module=self.mod_compra
                    iof_pct_vet = target_module.iof_compra.value
                    self.vet_calculado=self.taxa_efetiva_calculada*(1-iof_pct_vet)
                    self.accordion_esquerda.selected_index = 0
                    self.accordion_direita.selected_index = None
                else: # VENDA
                    self.taxa_efetiva_calculada=taxa_comercial_pura*(1+(spread_percentual/100))
                    op_str=f"Taxa Cambial (+{spread_percentual}%)"
                    target_module=self.mod_venda
                    iof_pct_vet = target_module.iof_venda.value
                    self.vet_calculado=self.taxa_efetiva_calculada*(1+iof_pct_vet)
                    self.accordion_direita.selected_index = 0
                    self.accordion_esquerda.selected_index = None

                self.last_brl_value = self.last_me_value * self.taxa_efetiva_calculada
                self.receita_operacao = abs(taxa_comercial_pura - self.taxa_efetiva_calculada) * self.last_me_value

                self.mod_compra.limpar_state()
                self.mod_venda.limpar_state()
                target_module.valor_brl_calculado.value = self.last_brl_value

                timestamp=datetime.strptime(cotacao_info['create_date'],'%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
                self.taxa_display.value = (f"<div style='background-color:#f0f7ff; padding:10px; border-radius:5px;'><b>Taxa Comercial ({moeda_sigla}):</b> R$ {taxa_comercial_pura:.4f}<br><b>{op_str}:</b> <span style='color:blue;font-size:1.2em;font-weight:bold;'>R$ {self.taxa_efetiva_calculada:.4f}</span><br><b>V.E.T ({iof_pct_vet*100:.2f}% IOF):</b> <span style='color:purple;font-weight:bold;'>R$ {self.vet_calculado:.4f}</span><br><span style='font-size:11px;'><i>Cotação API de {timestamp}</i></span><hr><b>Operação preparada. Verifique a seção correspondente.</b></div>")
                
                target_module.calcular(None)
            except requests.exceptions.RequestException:
                self.taxa_display.value=f"<b style='color:red'>Erro de conexão.</b>"
            except Exception as e:
                self.taxa_display.value=f"<b style='color:red'>Erro inesperado.</b>"
                print(traceback.format_exc())
            finally:
                self.compra_button.disabled=False
                self.venda_button.disabled=False

    def start(self):
        # Injeta o CSS na página
        display(HTML(self.get_ticker_css()))

        intro_text=widgets.HTML("<h3>Bem-vindo à Calculadora de Câmbio do Gabrielino</h3><p><b>1.</b> Preencha os dados no Gerenciador. <b>2.</b> Clique em COMPRA ou VENDA para calcular e abrir a seção correspondente.</p>")
        
        # Layout principal com margem para evitar sobreposição
        main_layout = widgets.VBox([
            self.ticker_bar,
            widgets.HTML("<div class='main-content'></div>"),  # Espaço para a ticker bar
            intro_text,
            self.gerenciador_layout,
            widgets.HTML("<hr><h4>Módulos de Cálculo:</h4>"),
            self.modulos_layout,
            widgets.HTML("<h4>Log de Erros:</h4>"),
            debug_output
        ])

        display(main_layout)

# --- Ponto de Entrada ---
if __name__ == "__main__":
    app = CalculadoraCambioApp()
    app.start()