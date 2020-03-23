```mermaid
graph TD
    V{{Verizon}} -->G{{"Gimli 🗄️"}}
    subgraph gimli-net
        G  --> XG(US-16-XG)
        XG --> U8(US-8-60W)
        XG --> M(Mikrotik)
        XG -->L["👣littlefoot 🗄️"]
        U8 -->UAP((UAP))
        UAP-->PI2[PI-2]
        UAP-->D[User Devices]
        UAP-->SH[Shield]
        M--> UP[Upstairs]
    end
    subgraph falcon-net
        G-->R{{R7000}}
        R-->N8(Netgear)
        R-->NW((Wifi))
        NW-->PI1[PI-1]
        NW-->G0[GoogleHome]
        NW-->G1[G0-1]
        NW-->G2[G0-2]
        NW-->G3[G0-3]
        NW-->G4[GA-1]
        NW-->OY[Onkyo]
        NW-->VZ[Vizio]
        N8-->C[Camera 1]
        N8-->C2[Camera 2]
        R-->H[Hue]
        R-->B[Printer]
    end
```