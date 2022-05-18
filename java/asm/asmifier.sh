# $1 is a .class file like #my/UnsignedByteToFloatSamplerConverter.class
/usr/lib/jvm/java-8-openjdk-amd64/bin/java -classpath /home/albert/Programming/fiji-new/Fiji.app/jars/imglib2-5.12.0.jar:/home/albert/Programming/fiji-new/Fiji.app/jars/asm-7.1.jar://home/albert/Programming/fiji-new/Fiji.app/jars/asm-util-7.1.jar org.objectweb.asm.util.ASMifier $1
