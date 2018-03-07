from zipfile import ZIP_DEFLATED
from tools import package

CONFIG = 'config.ini'

def main():
    control = package.Control()

    file = control.makePackage()
    print 'create package: {}'.format(file)
    
    file = control.makePackage(package.SECTION_RELEASE, compression=ZIP_DEFLATED)
    print 'create package: {}'.format(file)


if __name__ == "__main__":
    main()
