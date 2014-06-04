#!/usr/bin/env python2

import sys,datetime,time,pcapy,csv,json,socket,smtplib
from impacket.ImpactPacket import *
from impacket.ImpactDecoder import *
from PyQt4 import QtCore, QtGui
import mainWin

class captureThread(QtCore.QThread):
    """
    capture the packets and save them in list, 'packets' with structure{time:,packet:,header:}
    """
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.devices = pcapy.findalldevs()
        self.dev=str(self.devices[0])
        #~ self.dev='ppp0' 
        self.packets=[]
        #~ print 'capt started'
        self.stopSig=1
        self.devChanged=0

    def run(self):
        #~ print 'capT started on',self.dev     
        
        
        self.cap = pcapy.open_live(self.dev , 65536 , 1 , 0)
        while(1) :
            #~ print 'new loop'

            if self.stopSig:
                #~ print 'sleeping'
                time.sleep(0.1)
                continue
            if self.devChanged:
                #~ print 'dev changed'
                self.cap = pcapy.open_live(self.dev , 65536 , 1 , 0)
                self.devChanged=0
            try:
                #~ print 'running1'             
                (self.header, self.packet) = self.cap.next()
                #~ print 'running2'   
                self.timePacket={}
                self.timePacket['time']=datetime.datetime.now()
                self.timePacket['packet']=self.packet
                self.timePacket['header']=self.header
                self.packets.append(self.timePacket)
                #~ print 'capt',self.timePacket
            except pcapy.PcapError:
                continue
                
        return
        
    def __del__(self):
        self.wait()

class decodeThread(QtCore.QThread):
    """
    decode the packets captured in capture thread
    """
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.decodedPackets=[]
        self.ipHistory=[]
        
        self.index=1
        self.packetData={}
        self.monSite=[]
        self.toMail=[]
        self.begining=datetime.datetime.now()
    
    def mail(self):
        print self.toMail
        
        self.details=''
        for i in self.toMail:
            self.details+=i[1]+' : '+i[0]+'\n'
        self.msg = "\r\n".join(["Subject: Site monitor Report","",self.details])
        server = smtplib.SMTP('smtp.gmail.com:587')  
        server.ehlo()
        server.starttls()  
        server.login(MainWin.emailAdd,MainWin.emailPass)  
        server.sendmail(MainWin.emailAdd, MainWin.emailAdd, self.msg)  
        server.quit()
        
        self.packetData={}
        self.monSite=[]
        self.toMail=[]
        self.begining=datetime.datetime.now()

    def run(self):       
        #~ print 'decT started'
        
        self.tdelta=datetime.timedelta(seconds=MainWin.seconds)
        while(1) :
            if len(MainWin.CaptureThread.packets)<1:
                time.sleep(0.1)
                continue            
            try:
                self.decodedPacket={}                
                self.packetD=MainWin.CaptureThread.packets.pop()
                self.packet=self.packetD['packet']
                
                if MainWin.CaptureThread.dev[0]=='p':                    
                    self.decoder= LinuxSLLDecoder().decode(self.packet)   #ppp0
                else:
                    self.decoder= EthDecoder().decode(self.packet)
                self.ip=self.decoder.child()  #internet layer
                self.trans=self.ip.child()#transport layer
                self.transData=self.trans.child()
                
                self.time=self.packetD['time']
                self.protocol=''
                self.srcIp=''
                self.srcPort=' '
                self.dstIp=''
                self.dstPort=' '
                self.dstAdd=''
                
                if self.ip.get_ip_p() == UDP.protocol:
                    self.srcIp=self.ip.get_ip_src()
                    self.dstIp=self.ip.get_ip_dst()                      
                    self.protocol= 'UDP'
                    self.dstPort=self.trans.get_uh_dport()
                    self.srcPort=self.trans.get_uh_sport()
                    
                if self.ip.get_ip_p() == TCP.protocol:
                    self.srcIp=self.ip.get_ip_src()
                    self.dstIp=self.ip.get_ip_dst()
                    self.protocol= 'TCP'
                    self.dstPort=self.trans.get_th_dport()
                    self.srcPort=self.trans.get_th_sport()
                    
                if self.ip.get_ip_p() == ICMP.protocol:
                    self.srcIp=self.ip.get_ip_src()
                    self.dstIp=self.ip.get_ip_dst()
                    self.protocol= 'ICMP'
                
                self.decodedPacket={'time':self.time,'protocol':self.protocol,'srcIp':self.srcIp,'srcPort':self.srcPort,'dstIp':self.dstIp,'dstPort':self.dstPort}
                #~ print self.decodedPacket
                self.decodedPackets.append(self.decodedPacket)
                #~ self.ipHistory.append(self.dstIp)
                
                #~ if self.dstIp in MainWin.monIp:                    
                    #~ self.site=MainWin.monList[str(self.dstIp)]                    
                    #~ if self.site not in self.monSite:                        
                        #~ self.monSite.append(self.site)
                        #~ self.toMail.append([self.site,self.time.strftime('%Y-%m-%d %H:%M:%S')])
                        
                #~ if (len(self.toMail)>0) and ((datetime.datetime.now()-self.begining) > self.tdelta):
                    #~ self.mail()
                
                self.leftOutput ='{0} . {1} || {2} : {3}  => {4} : {5}  ||  {6}'.format(self.index,self.time.strftime('%Y-%m-%d %H:%M:%S'),self.srcIp,self.srcPort,self.dstIp,self.dstPort,self.protocol)
                self.rightOutput=str(self.transData)
                self.packetData[self.leftOutput]=self.rightOutput
                
                self.emit( QtCore.SIGNAL('updateLeft(QString)'), self.leftOutput)
                self.emit( QtCore.SIGNAL('updateRight(QString)'), self.rightOutput )
                self.emit( QtCore.SIGNAL('updateNumofPac(QString)'), 'Number of Packets captured : '+str(self.index) )
                self.index+=1
                
            except Exception, e:
                print '[ErrorDecodeThread]',str(e)
                
        return
        
    def __del__(self):
        self.wait()

class mainWindow(QtGui.QMainWindow,mainWin.Ui_MainWindow):    
    """
    main window. when main method executed WorkThread instance is made and starts running.
    """
    def __init__(self,parent=None):
        super(mainWindow,self).__init__(parent)
        self.setupUi(self)
        self.connectActions()
        self.monIp=[]
        self.monSite=[]
        self.monList={}
        self.userData={'pass':'pass','emailAdd':'youremail@gmail.com','emailPass':'pass','seconds':60}
        self.password=self.userData['pass']
        self.emailAdd=self.userData['emailAdd']
        self.emailPass=self.userData['emailPass']
        self.seconds=int(self.userData['seconds'])
        self.getUData()
        self.admin=0
    
    def getUData(self):
        with open('udata','a+') as udata:
            try:
                uda=json.load(udata)
                self.password=uda['pass']
                self.emailAdd=uda['emailAdd']
                self.emailPass=uda['emailPass']
                self.seconds=int(uda['seconds']) 
            except:
                pass
            
    def monitor(self):
        self.mon=open('moniteredIp','a+')
        self.monContent=[line.rstrip() for line in self.mon]
        for i in self.monContent:
            if len(i)>0:                
                self.monIp.append(i)
        #~ print self.monIp
        self.mon.close()
        
        self.monSitef=open('moniteredSite','a+') 
        self.monContentSite=[line.rstrip() for line in self.monSitef]
        for i in self.monContentSite:
            if len(i)>0:                
                self.monSite.append(i)
        #~ print self.monSite
        self.monSitef.close()
        
        if len(self.monIp)!=len(self.monSite):
            print 'Site monitoring may not function correct  !!!'
        
        for i in xrange(len(self.monIp)):
            self.monList[self.monIp[i]]=self.monSite[i]
        #~ print 'mon list',self.monList
        
    def main(self):
        self.sniffer()
        self.nciCmbBox.addItems(self.CaptureThread.devices)
        #~ self.monitor()
        #~ print self.workThread.devices
        self.show()
        
    def connectActions(self):        
        self.startBtn.clicked.connect(self.startCapture)
        self.stopBtn.clicked.connect(self.stopCapture)
        self.leftList.itemSelectionChanged.connect(self.dispalyData)
        #~ self.siteBlockereBtn.clicked.connect(self.site_block)
        #~ self.adminBtn.clicked.connect(self.adminLog)
        #~ self.userBtn.clicked.connect(self.userLog)
        #~ self.preferenceBtn.clicked.connect(self.preferences)
        self.connect(self.nciCmbBox, QtCore.SIGNAL('activated(QString)'), self.combo_chosen)
        #~ self.saveBtn.clicked.connect(self.save_file)
        #~ self.historyBtn.clicked.connect(self.showHistory)
    #~ 
    def userLog(self):
        if self.admin==1:
            self.admin=0
            self.mode.setText('Mode : Normal                  ')
        else:
            pass
        
        
    def preferences(self):
        if self.admin==0:
            self.show_warning()
        else:
            self.Preferences=preferences()
            self.Preferences.main()
    
    def save_file(self):
        if self.admin==0:
            self.show_warning()
        else:
            self.SaveFile=saveWindow()
            self.SaveFile.main()
    
    def showHistory(self):
        if self.admin==0:
            self.show_warning()
        else:
            self.History=historyWindow()
            self.History.main()
        
    def combo_chosen(self,interface):
        #~ print self.workThread.dev
        self.CaptureThread.dev=str(interface)
        self.CaptureThread.devChanged=1
        #~ print self.CaptureThread.dev
    
    def show_warning(self):
        self.WarningWin=warning()
        self.WarningWin.main()
        
    def adminLog(self):
        if self.admin==1:
            pass
        else:
            self.AdminLog=addminLog()
            self.AdminLog.main()            
    
    def site_block(self):
        if self.admin==0:
            self.show_warning()
        else:
            self.SiteBlock=siteBlock()
            self.SiteBlock.main()           
            
        #~ self.Authenticate=authenticate()
        #~ self.Authenticate.main()  
        
    def startCapture(self):
        self.status.setText('Status : Running    ')
        #~ print 'capturing started on ',self.CaptureThread.dev
        self.CaptureThread.stopSig=0
        
    def stopCapture(self):
        self.CaptureThread.stopSig=1
        self.status.setText('Status : Stopped    ')
        
    def dispalyData(self):
        item=self.leftList.selectedItems()
        self.rightLabel.setText(self.DecodeThread.packetData[str(item[0].text())])
        
    def sniffer(self):
        self.CaptureThread = captureThread()
        self.CaptureThread.start()     
        self.DecodeThread = decodeThread()
        self.DecodeThread.start()
              
        self.connect( self.DecodeThread, QtCore.SIGNAL("updateLeft(QString)"), self.leftList.addItem)
        self.connect( self.DecodeThread, QtCore.SIGNAL("updateRight(QString)"), self.rightLabel.setText)
        self.connect( self.DecodeThread, QtCore.SIGNAL("updateNumofPac(QString)"), self.numofPackets.setText)
        
        #~ self.ResolveThread = resolveThread()
        #~ self.ResolveThread.start()  
                
if __name__=='__main__':
    app = QtGui.QApplication(sys.argv)
    MainWin=mainWindow()
    MainWin.main()
    sys.exit(app.exec_())
